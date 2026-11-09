package com.asknote.config;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.asknote.entity.Member;
import com.asknote.repository.MemberRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

class AdminInitializerTest {

    private MemberRepository memberRepository;
    private AdminInitializer initializer;

    @BeforeEach
    void setUp() {
        memberRepository = mock(MemberRepository.class);
        PasswordEncoder passwordEncoder = mock(PasswordEncoder.class);
        given(passwordEncoder.encode(any())).willReturn("$2a$10$hash");
        initializer = new AdminInitializer(memberRepository, passwordEncoder);
        ReflectionTestUtils.setField(initializer, "adminEmail", "admin@test.com");
    }

    @Test
    void 규칙에_맞는_비밀번호면_관리자_생성() {
        ReflectionTestUtils.setField(initializer, "adminPassword", "Str0ng!Pass");

        initializer.run(null);

        verify(memberRepository).save(any(Member.class));
    }

    @Test
    void 약한_비밀번호면_관리자를_만들지_않음() {
        ReflectionTestUtils.setField(initializer, "adminPassword", "admin");

        initializer.run(null);

        verify(memberRepository, never()).save(any(Member.class));
    }

    @Test
    void 이미_있으면_건드리지_않음() {
        ReflectionTestUtils.setField(initializer, "adminPassword", "Str0ng!Pass");
        given(memberRepository.existsByEmail("admin@test.com")).willReturn(true);

        initializer.run(null);

        verify(memberRepository, never()).save(any(Member.class));
    }
}
