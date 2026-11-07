package com.asknote.controller;

import com.asknote.common.ApiResponse;
import com.asknote.common.PageResponse;
import com.asknote.dto.chat.ChatHistoryResponse;
import com.asknote.dto.chat.ChatStreamRequest;
import com.asknote.service.ChatHistoryService;
import com.asknote.service.ChatStreamService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/** AI 채팅 API — 질문(스트리밍) · 기록 목록 (피드백 PATCH 는 Backend 2 가 이 컨트롤러에 추가) */
@RestController
@RequestMapping("/api/chats")
@RequiredArgsConstructor
public class ChatController {

    private final ChatStreamService chatStreamService;
    private final ChatHistoryService chatHistoryService;

    /** 내 질문 기록 목록 (최신순, 페이지 번호는 0부터, 기본 size=10) */
    @GetMapping
    public ApiResponse<PageResponse<ChatHistoryResponse>> list(
            @RequestParam(name = "page", defaultValue = "0") int page,
            @RequestParam(name = "size", defaultValue = "10") int size) {
        return ApiResponse.ok(chatHistoryService.getMyChats(page, size));
    }

    /** 검증 · READY 문서 확인은 스트림 시작 전에 끝냄 → 실패하면 일반 JSON 오류 (400 · 401) */
    @PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public ResponseEntity<SseEmitter> stream(@Valid @RequestBody ChatStreamRequest request) {
        ChatStreamService.ChatContext context = chatStreamService.prepare(request);
        return ResponseEntity.ok()
                .header("Cache-Control", "no-cache")
                .header("X-Accel-Buffering", "no") // nginx 버퍼링 끄기 (응답 단위)
                .contentType(MediaType.TEXT_EVENT_STREAM)
                .body(chatStreamService.stream(context));
    }
}
