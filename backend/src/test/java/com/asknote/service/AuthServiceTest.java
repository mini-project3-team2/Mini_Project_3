package com.asknote.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.asknote.common.audit.AuditLogger;
import com.asknote.common.exception.ErrorCode;
import com.asknote.dto.auth.LoginRequest;
import com.asknote.entity.Member;
import com.asknote.repository.MemberRepository;
import com.asknote.repository.RefreshTokenRepository;
import com.asknote.security.JwtTokenProvider;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

class AuthServiceTest {

    private MemberRepository memberRepository;
    private PasswordEncoder passwordEncoder;
    private AuthService authService;

    @BeforeEach
    void setUp() {
        memberRepository = mock(MemberRepository.class);
        passwordEncoder = mock(PasswordEncoder.class);
        authService = new AuthService(memberRepository, mock(RefreshTokenRepository.class), passwordEncoder,
                mock(JwtTokenProvider.class), mock(AuditLogger.class));
        ReflectionTestUtils.setField(authService, "maxAttempts", 5);
        ReflectionTestUtils.setField(authService, "lockMinutes", 15L);
        given(passwordEncoder.encode(anyString())).willReturn("$2a$10$dummy");
    }

    @Test
    void 없는_이메일도_BCrypt_비교를_한_번_수행하고_401() {
        given(memberRepository.findByEmailForUpdate("nobody@test.com")).willReturn(Optional.empty());

        assertThatThrownBy(() -> authService.login(new LoginRequest("nobody@test.com", "Wrong1234!"), "127.0.0.1"))
                .extracting("errorCode").isEqualTo(ErrorCode.INVALID_CREDENTIALS);
        // 응답 시간으로 가입 여부를 알 수 없도록, 있는 계정과 같은 비교를 한 번 거친다
        verify(passwordEncoder).matches("Wrong1234!", "$2a$10$dummy");
    }

    @Test
    void 비밀번호가_72바이트를_넘으면_BCrypt_에_넘기지_않고_401_실패횟수_증가() {
        Member member = Member.createMember("student@test.com", "$2a$10$real");
        given(memberRepository.findByEmailForUpdate("student@test.com")).willReturn(Optional.of(member));
        String tooLong = "a".repeat(73);

        assertThatThrownBy(() -> authService.login(new LoginRequest("student@test.com", tooLong), "127.0.0.1"))
                .extracting("errorCode").isEqualTo(ErrorCode.INVALID_CREDENTIALS);
        verify(passwordEncoder, never()).matches(eq(tooLong), anyString());
        assertThat(member.getFailedLoginCount()).isEqualTo(1);
    }
}
