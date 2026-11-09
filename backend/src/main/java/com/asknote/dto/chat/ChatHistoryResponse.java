package com.asknote.dto.chat;

import com.asknote.entity.ChatHistory;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;

/** 질문 기록 목록의 content 항목 (API 설계서 5.2) — 상세 화면 없이 목록에서 질문 · 답변 · 출처를 바로 보여준다 */
public record ChatHistoryResponse(
        Long id,
        String question,
        String answer,
        List<ChatSource> sources,
        /** HELPFUL / NOT_HELPFUL / null(미선택) */
        String feedback,
        LocalDateTime createdAt
) {

    public static ChatHistoryResponse of(ChatHistory chat, List<ChatSource> sources) {
        return new ChatHistoryResponse(
                chat.getId(),
                chat.getQuestion(),
                chat.getAnswer(),
                sources,
                chat.getFeedback() == null ? null : chat.getFeedback().name(),
                chat.getCreatedAt() == null ? null : chat.getCreatedAt().truncatedTo(ChronoUnit.SECONDS));
    }
}
