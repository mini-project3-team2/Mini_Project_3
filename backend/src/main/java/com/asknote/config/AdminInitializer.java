package com.asknote.config;

import com.asknote.entity.Member;
import com.asknote.repository.MemberRepository;
import java.util.Locale;
import java.util.regex.Pattern;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 관리자 계정 생성 — 환경 변수 ADMIN_EMAIL · ADMIN_PASSWORD (Flyway 에 비밀번호를 넣지 않음)
 * 값이 비어 있으면 만들지 않고, 이미 있으면 건드리지 않는다 (ADMIN_PASSWORD 를 바꿔도 기존 계정에는 반영되지 않음 → 경고 로그)
 * 비밀번호가 회원가입 규칙(8~20자, 영문 · 숫자 · 특수문자)보다 약하면 만들지 않는다
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AdminInitializer implements ApplicationRunner {

    /** SignupRequest 와 같은 비밀번호 규칙 */
    static final Pattern PASSWORD_RULE =
            Pattern.compile("^(?=.*[A-Za-z])(?=.*\\d)(?=.*[^A-Za-z\\d\\s])\\S{8,20}$");

    private final MemberRepository memberRepository;
    private final PasswordEncoder passwordEncoder;

    @Value("${ADMIN_EMAIL:}")
    private String adminEmail;

    @Value("${ADMIN_PASSWORD:}")
    private String adminPassword;

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        if (adminEmail.isBlank() || adminPassword.isBlank()) {
            log.warn("ADMIN_EMAIL · ADMIN_PASSWORD 가 비어 있어 관리자 계정을 만들지 않습니다");
            return;
        }
        if (!PASSWORD_RULE.matcher(adminPassword).matches()) {
            log.error("ADMIN_PASSWORD 가 비밀번호 규칙(8~20자, 영문 · 숫자 · 특수문자)에 맞지 않아 관리자 계정을 만들지 않습니다");
            return;
        }
        String email = adminEmail.trim().toLowerCase(Locale.ROOT);
        if (memberRepository.existsByEmail(email)) {
            log.info("관리자 계정이 이미 있어 그대로 둡니다 (ADMIN_PASSWORD 를 바꿔도 기존 계정 비밀번호는 바뀌지 않음)");
            return;
        }
        memberRepository.save(Member.createAdmin(email, passwordEncoder.encode(adminPassword)));
        log.info("관리자 계정을 생성했습니다");
    }
}
