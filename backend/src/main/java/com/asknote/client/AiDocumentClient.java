package com.asknote.client;

import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import com.asknote.dto.ai.IngestResponse;
import java.time.Duration;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

/**
 * AI Module 자료 적재 · 청크 삭제 (API 설계서 6.1 · 6.2)
 * Spring MVC 요청 스레드에서 block() 으로 결과를 기다린다 (업로드는 동기 적재)
 */
@Slf4j
@Component
public class AiDocumentClient {

    private final WebClient aiWebClient;
    private final Duration ingestTimeout;
    private final Duration deleteTimeout;

    public AiDocumentClient(WebClient aiWebClient,
                            @Value("${ai.timeout.ingest-seconds}") long ingestSeconds,
                            @Value("${ai.timeout.delete-seconds}") long deleteSeconds) {
        this.aiWebClient = aiWebClient;
        this.ingestTimeout = Duration.ofSeconds(ingestSeconds);
        this.deleteTimeout = Duration.ofSeconds(deleteSeconds);
    }

    /**
     * 적재 — 422 는 본문 코드로 구분 (TOO_MANY_PAGES → TOO_MANY_PAGES, 그 밖 → TEXT_EXTRACTION_FAILED),
     * 그 밖의 오류 · 연결 실패 · 타임아웃은 AI_UNAVAILABLE (API 설계서 6.1)
     */
    public IngestResponse ingest(Long documentId, String ownerUuid, String documentName, byte[] content) {
        MultipartBodyBuilder body = new MultipartBodyBuilder();
        body.part("file", new ByteArrayResource(content))
                .filename(documentName)
                .contentType(MediaType.APPLICATION_PDF);
        body.part("documentId", String.valueOf(documentId));
        body.part("ownerUuid", ownerUuid);
        body.part("documentName", documentName);

        try {
            return aiWebClient.post()
                    .uri("/internal/documents")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(BodyInserters.fromMultipartData(body.build()))
                    .retrieve()
                    .onStatus(status -> status.value() == HttpStatus.UNPROCESSABLE_CONTENT.value(),
                            response -> response.bodyToMono(String.class)
                                    .defaultIfEmpty("")
                                    .flatMap(errorBody -> Mono.error(new BusinessException(unprocessable(errorBody)))))
                    .bodyToMono(IngestResponse.class)
                    .timeout(ingestTimeout)
                    .block();
        } catch (BusinessException e) {
            throw e;
        } catch (RuntimeException e) {
            log.warn("AI 적재 실패 documentId={} cause={}", documentId, e.toString());
            throw new BusinessException(ErrorCode.AI_UNAVAILABLE);
        }
    }

    /** AI 422 본문 {"error":"CODE"} 의 코드 → 화면용 오류 코드 (본문은 로그에 남기지 않음) */
    static ErrorCode unprocessable(String body) {
        return body.contains("\"TOO_MANY_PAGES\"") ? ErrorCode.TOO_MANY_PAGES : ErrorCode.TEXT_EXTRACTION_FAILED;
    }

    /** 청크 삭제 — 성공(2xx, AI 는 청크가 없어도 204)이면 true, 실패 · 타임아웃이면 false (예외를 던지지 않음, 판단은 호출하는 쪽) */
    public boolean deleteChunks(Long documentId, String ownerUuid) {
        try {
            aiWebClient.delete()
                    .uri(uri -> uri.path("/internal/documents/{id}")
                            .queryParam("ownerUuid", ownerUuid)
                            .build(documentId))
                    .retrieve()
                    .toBodilessEntity()
                    .timeout(deleteTimeout)
                    .block();
            return true;
        } catch (RuntimeException e) {
            log.warn("AI 청크 삭제 실패 documentId={} cause={}", documentId, e.toString());
            return false;
        }
    }
}
