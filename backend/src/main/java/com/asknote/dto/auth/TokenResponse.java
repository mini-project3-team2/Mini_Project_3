package com.asknote.dto.auth;

/** 로그인 · 토큰 재발급 응답 */
public record TokenResponse(
        String accessToken,
        String refreshToken,
        long expiresIn,
        MemberResponse member
) {
}
