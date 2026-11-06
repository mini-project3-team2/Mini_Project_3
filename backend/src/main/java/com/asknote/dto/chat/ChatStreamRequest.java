package com.asknote.dto.chat;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 질문 요청 (API 설계서 5.1)
 * TODO(RAG 소유자 우회 조치): ownerUuid 를 요청에서 받고 있음 → 취약점 재현 캡처 후 fix(security) 커밋에서 제거
 */
public record ChatStreamRequest(
        @NotBlank(message = "질문을 입력해 주세요")
        @Size(max = 1000, message = "질문은 1000자 이하여야 합니다")
        String question,

        String ownerUuid
) {
}
