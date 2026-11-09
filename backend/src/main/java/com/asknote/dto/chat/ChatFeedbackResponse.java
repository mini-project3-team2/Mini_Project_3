package com.asknote.dto.chat;

import com.asknote.entity.ChatHistory;

/** 답변 피드백 응답 (API 설계서 5.3) — {"id": 31, "feedback": "HELPFUL"} */
public record ChatFeedbackResponse(
        Long id,
        String feedback
) {

    public static ChatFeedbackResponse from(ChatHistory chat) {
        return new ChatFeedbackResponse(chat.getId(), chat.getFeedback() == null ? null : chat.getFeedback().name());
    }
}
