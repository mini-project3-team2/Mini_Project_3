package com.asknote.dto.chat;

import com.asknote.entity.Feedback;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

/**
 * 답변 피드백 요청 (API 설계서 5.3) — HELPFUL · NOT_HELPFUL 중 하나
 * enum 으로 바로 받으면 Jackson 이 숫자 0 · 1 을 순번으로 해석해 HELPFUL · NOT_HELPFUL 로 바꿔 버리므로
 * 문자열로 받아 정확히 두 값만 허용한 뒤 enum 으로 변환한다 (그 외 값 · 숫자 · null → 400 INVALID_INPUT)
 */
public record ChatFeedbackRequest(
        @NotNull(message = "피드백 값을 선택해 주세요")
        @Pattern(regexp = "HELPFUL|NOT_HELPFUL", message = "피드백 값은 HELPFUL 또는 NOT_HELPFUL 이어야 합니다")
        String feedback
) {

    /** @Valid 검증을 통과한 뒤에만 호출 */
    public Feedback toFeedback() {
        return Feedback.valueOf(feedback);
    }
}
