package com.asknote.dto.auth;

import jakarta.validation.constraints.NotBlank;

/** 로그인은 형식 검증을 하지 않는다 (틀린 형식도 401 INVALID_CREDENTIALS 로 같은 응답) */
public record LoginRequest(
        @NotBlank(message = "이메일을 입력해 주세요") String email,
        @NotBlank(message = "비밀번호를 입력해 주세요") String password
) {
}
