package com.asknote.security;

import com.asknote.common.exception.ErrorCode;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * Security 필터 단계(컨트롤러 밖)의 오류를 공통 응답 형식으로 쓴다
 * 문구는 ErrorCode 의 고정 값만 쓰므로 사용자 입력이 섞이지 않는다
 */
final class SecurityErrorWriter {

    private SecurityErrorWriter() {
    }

    static void write(HttpServletResponse response, ErrorCode code) throws IOException {
        response.setStatus(code.getStatus().value());
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType("application/json");
        response.getWriter().write(
                "{\"success\":false,\"data\":null,\"message\":\"" + code.getMessage()
                        + "\",\"code\":\"" + code.name() + "\"}");
    }
}
