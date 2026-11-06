package com.asknote.security;

import com.asknote.common.audit.AuditLogger;
import com.asknote.common.exception.ErrorCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

/** 로그인은 했지만 권한이 없음 (예: MEMBER 가 /actuator/**) → 403 FORBIDDEN + 감사 로그 */
@Component
@RequiredArgsConstructor
public class JsonAccessDeniedHandler implements AccessDeniedHandler {

    private final AuditLogger auditLogger;

    @Override
    public void handle(HttpServletRequest request, HttpServletResponse response,
                       AccessDeniedException accessDeniedException) throws IOException {
        auditLogger.accessDenied(request.getMethod() + " " + request.getRequestURI(), request.getRemoteAddr());
        SecurityErrorWriter.write(response, ErrorCode.FORBIDDEN);
    }
}
