package com.asknote.service;

import com.asknote.client.AiQueryClient;
import com.asknote.common.auth.CurrentMemberProvider;
import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import com.asknote.dto.ai.QueryRequest;
import com.asknote.dto.chat.ChatStreamRequest;
import com.asknote.entity.ChatHistory;
import com.asknote.entity.DocumentStatus;
import com.asknote.entity.Member;
import com.asknote.repository.ChatHistoryRepository;
import com.asknote.repository.DocumentRepository;
import java.io.IOException;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import reactor.core.Disposable;
import tools.jackson.databind.ObjectMapper;

/**
 * 질문 → AI 답변 SSE 중계 (API 설계서 5.1 · 6.3)
 * - 스트림 시작 전 검증 오류는 일반 JSON 응답 (prepare 에서 예외)
 * - sources · token 은 그대로 중계, token 은 모아 두었다가 done 때 기록 저장 후 {"chatId"} 전송
 * - AI error · 타임아웃 · 연결 오류: 원인은 로그에만, 화면에는 고정 문구, 기록 저장 안 함
 * - 화면 연결이 끊기면 AI 구독도 끊는다 (기록 저장 안 함)
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ChatStreamService {

    static final String ERROR_MESSAGE = "{\"message\":\"지금은 답변할 수 없습니다. 잠시 후 다시 시도해 주세요\"}";

    private final CurrentMemberProvider currentMemberProvider;
    private final DocumentRepository documentRepository;
    private final ChatHistoryRepository chatHistoryRepository;
    private final AiQueryClient aiQueryClient;
    private final ObjectMapper objectMapper;

    /** token 이벤트 data {"text": "..."} */
    public record TokenData(String text) {
    }

    /** 검증된 질문 정보 */
    public record ChatContext(Member member, String question, String ownerUuid, List<Long> documentIds) {
    }

    /**
     * 스트림 시작 전 준비 — 질문할 회원 · READY 문서 id 확정
     * RAG 소유자 우회 조치: ownerUuid · documentIds 는 JWT 회원에게서만 만든다 (요청 값 사용 안 함)
     */
    public ChatContext prepare(ChatStreamRequest request) {
        Member member = currentMemberProvider.getCurrentMember();
        List<Long> documentIds = documentRepository.findIdsByMemberIdAndStatus(member.getId(), DocumentStatus.READY);
        if (documentIds.isEmpty()) {
            throw new BusinessException(ErrorCode.NO_DOCUMENT);
        }
        return new ChatContext(member, request.question().trim(), member.getUuid(), documentIds);
    }

    public SseEmitter stream(ChatContext context) {
        // 화면 쪽 연결 제한: AI 타임아웃(60초)보다 여유 있게
        SseEmitter emitter = new SseEmitter(aiQueryClient.getStreamTimeout().plusSeconds(30).toMillis());
        StringBuilder answer = new StringBuilder();
        AtomicBoolean finished = new AtomicBoolean(false);
        String[] sourcesJson = {null};

        Disposable subscription = aiQueryClient
                .stream(new QueryRequest(context.question(), context.ownerUuid(), context.documentIds()))
                .subscribe(
                        event -> handleEvent(event, emitter, answer, sourcesJson, finished, context),
                        error -> {
                            log.warn("AI 스트리밍 실패 cause={}", error.toString());
                            fail(emitter, finished);
                        },
                        () -> {
                            if (!finished.get()) {
                                log.warn("AI 스트림이 done 없이 끝남");
                                fail(emitter, finished);
                            }
                        });

        emitter.onCompletion(subscription::dispose);
        emitter.onTimeout(() -> {
            subscription.dispose();
            fail(emitter, finished);
        });
        emitter.onError(e -> subscription.dispose());
        return emitter;
    }

    private void handleEvent(ServerSentEvent<String> event, SseEmitter emitter, StringBuilder answer,
                             String[] sourcesJson, AtomicBoolean finished, ChatContext context) {
        if (finished.get()) {
            return;
        }
        String name = event.event() == null ? "" : event.event();
        String data = event.data() == null ? "" : event.data();
        switch (name) {
            case "sources" -> {
                sourcesJson[0] = validJsonOrNull(data);
                send(emitter, "sources", data, finished);
            }
            case "token" -> {
                answer.append(readText(data));
                send(emitter, "token", data, finished);
            }
            case "done" -> {
                if (!finished.compareAndSet(false, true)) {
                    return;
                }
                ChatHistory saved = chatHistoryRepository.save(
                        new ChatHistory(context.member(), context.question(), answer.toString(), sourcesJson[0]));
                try {
                    emitter.send(SseEmitter.event().name("done").data("{\"chatId\":" + saved.getId() + "}"));
                    emitter.complete();
                } catch (IOException e) {
                    emitter.completeWithError(e);
                }
            }
            case "error" -> {
                log.warn("AI error 이벤트 data={}", data); // 원인 코드는 로그에만
                fail(emitter, finished);
            }
            default -> log.debug("알 수 없는 AI 이벤트 {}", name);
        }
    }

    private void send(SseEmitter emitter, String name, String data, AtomicBoolean finished) {
        try {
            emitter.send(SseEmitter.event().name(name).data(data));
        } catch (IOException | IllegalStateException e) {
            finished.set(true); // 화면 연결 끊김 → onError 에서 AI 구독 해제
        }
    }

    private void fail(SseEmitter emitter, AtomicBoolean finished) {
        if (!finished.compareAndSet(false, true)) {
            return;
        }
        try {
            emitter.send(SseEmitter.event().name("error").data(ERROR_MESSAGE));
            emitter.complete();
        } catch (IOException | IllegalStateException e) {
            emitter.completeWithError(e);
        }
    }

    private String readText(String tokenJson) {
        try {
            TokenData token = objectMapper.readValue(tokenJson, TokenData.class);
            return token.text() == null ? "" : token.text();
        } catch (RuntimeException e) {
            return "";
        }
    }

    private String validJsonOrNull(String json) {
        try {
            objectMapper.readTree(json);
            return json;
        } catch (RuntimeException e) {
            return null;
        }
    }
}
