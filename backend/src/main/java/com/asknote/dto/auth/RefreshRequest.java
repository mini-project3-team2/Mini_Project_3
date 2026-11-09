package com.asknote.dto.auth;

import jakarta.validation.constraints.NotBlank;

/** 토큰 재발급 · 로그아웃 요청 */
public record RefreshRequest(
        @NotBlank(message = "입력값을 확인해 주세요") String refreshToken
) {
}
