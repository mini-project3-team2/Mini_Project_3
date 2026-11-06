package com.asknote.common.audit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * 감사 로그 (로거 이름 AUDIT) — 이메일은 마스킹, 비밀번호 · 토큰은 절대 기록하지 않는다
 * 예: AUDIT LOGIN_FAILURE email=st***@test.com ip=127.0.0.1
 */
@Component
public class AuditLogger {

    private static final Logger log = LoggerFactory.getLogger("AUDIT");

    public void signup(String email, String ip) {
        log.info("SIGNUP email={} ip={}", mask(email), ip);
    }

    public void loginSuccess(String email, String ip) {
        log.info("LOGIN_SUCCESS email={} ip={}", mask(email), ip);
    }

    public void loginFailure(String email, String ip) {
        log.warn("LOGIN_FAILURE email={} ip={}", mask(email), ip);
    }

    public void accountLocked(String email, String ip) {
        log.warn("ACCOUNT_LOCKED email={} ip={}", mask(email), ip);
    }

    public void logout(String email, String ip) {
        log.info("LOGOUT email={} ip={}", mask(email), ip);
    }

    public void refreshFailure(String ip) {
        log.warn("REFRESH_FAILURE ip={}", ip);
    }

    public void accessDenied(String target, String ip) {
        log.warn("ACCESS_DENIED target={} ip={}", target, ip);
    }

    /** student@test.com → st***@test.com */
    static String mask(String email) {
        if (email == null) {
            return "-";
        }
        String value = email.replaceAll("[\\r\\n]", "");
        int at = value.indexOf('@');
        if (at <= 0) {
            return "***";
        }
        String local = value.substring(0, at);
        String visible = local.length() <= 2 ? local.substring(0, 1) : local.substring(0, 2);
        return visible + "***" + value.substring(at);
    }
}
