package com.asknote.client;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.ClientResponse;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

/** AI 적재 오류 응답 → 화면용 오류 코드 변환 (API 설계서 6.1) — 실제 서버 없이 응답만 흉내 낸다 */
class AiDocumentClientTest {

    private static AiDocumentClient clientReturning(HttpStatus status, String body) {
        WebClient webClient = WebClient.builder()
                .exchangeFunction(request -> Mono.just(ClientResponse.create(status)
                        .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                        .body(body)
                        .build()))
                .build();
        return new AiDocumentClient(webClient, 5, 5);
    }

    private static void ingest(AiDocumentClient client) {
        client.ingest(1L, "8f14e45f-ceea-467f-a0e6-1a2b3c4d5e6f", "note.pdf", "%PDF-1.4".getBytes());
    }

    @Test
    void AI_422_TOO_MANY_PAGES_는_TOO_MANY_PAGES() {
        AiDocumentClient client = clientReturning(HttpStatus.UNPROCESSABLE_CONTENT, "{\"error\":\"TOO_MANY_PAGES\"}");

        assertThatThrownBy(() -> ingest(client))
                .isInstanceOf(BusinessException.class)
                .extracting("errorCode").isEqualTo(ErrorCode.TOO_MANY_PAGES);
    }

    @Test
    void 그_밖의_AI_422_는_TEXT_EXTRACTION_FAILED() {
        AiDocumentClient client = clientReturning(HttpStatus.UNPROCESSABLE_CONTENT, "{\"error\":\"TEXT_EXTRACTION_FAILED\"}");

        assertThatThrownBy(() -> ingest(client))
                .extracting("errorCode").isEqualTo(ErrorCode.TEXT_EXTRACTION_FAILED);
    }

    @Test
    void AI_500_은_AI_UNAVAILABLE() {
        AiDocumentClient client = clientReturning(HttpStatus.INTERNAL_SERVER_ERROR, "{\"error\":\"INTERNAL_ERROR\"}");

        assertThatThrownBy(() -> ingest(client))
                .extracting("errorCode").isEqualTo(ErrorCode.AI_UNAVAILABLE);
    }
}
