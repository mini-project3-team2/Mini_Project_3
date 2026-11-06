package com.asknote.dto.chat;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 질문 요청 (API 설계서 5.1)
 * RAG 소유자 우회 조치: 검색 소유자(ownerUuid)는 요청에서 받지 않는다 — 항상 JWT 의 회원 (요청에 넣어도 무시됨)
 */
public record ChatStreamRequest(
        @NotBlank(message = "질문을 입력해 주세요")
        @Size(max = 1000, message = "질문은 1000자 이하여야 합니다")
        String question
) {
}
