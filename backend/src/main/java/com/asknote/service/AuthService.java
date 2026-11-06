package com.asknote.service;

import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import com.asknote.dto.auth.LoginRequest;
import com.asknote.dto.auth.MemberResponse;
import com.asknote.dto.auth.SignupRequest;
import com.asknote.dto.auth.TokenResponse;
import com.asknote.entity.Member;
import com.asknote.entity.RefreshToken;
import com.asknote.repository.MemberRepository;
import com.asknote.repository.RefreshTokenRepository;
import com.asknote.security.JwtTokenProvider;
import com.asknote.security.RefreshTokenUtil;
import java.time.LocalDateTime;
import java.util.Locale;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final MemberRepository memberRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;

    @Value("${jwt.refresh-expiration}")
    private long refreshExpirationMillis;

    @Transactional
    public MemberResponse signup(SignupRequest request) {
        String email = normalize(request.email());
        if (memberRepository.existsByEmail(email)) {
            throw new BusinessException(ErrorCode.DUPLICATE_EMAIL);
        }
        Member member = Member.createMember(email, passwordEncoder.encode(request.password()));
        return MemberResponse.from(memberRepository.save(member));
    }

    /**
     * 로그인 — 이메일이 없든 비밀번호가 틀리든 같은 401 (이메일 존재 여부를 알려주지 않음)
     * TODO(Brute Force 조치): 현재는 실패 횟수 제한이 없음 → 취약점 재현 캡처 후 fix(security) 커밋에서 잠금 추가
     */
    @Transactional
    public TokenResponse login(LoginRequest request) {
        Member member = memberRepository.findByEmail(normalize(request.email()))
                .filter(m -> passwordEncoder.matches(request.password(), m.getPassword()))
                .orElseThrow(() -> new BusinessException(ErrorCode.INVALID_CREDENTIALS));
        return issueTokens(member);
    }

    private TokenResponse issueTokens(Member member) {
        String accessToken = jwtTokenProvider.createAccessToken(member.getUuid(), member.getRole().name());
        String refreshToken = RefreshTokenUtil.generate();
        LocalDateTime expiresAt = LocalDateTime.now().plusNanos(refreshExpirationMillis * 1_000_000);
        refreshTokenRepository.save(new RefreshToken(member, RefreshTokenUtil.hash(refreshToken), expiresAt));
        return new TokenResponse(accessToken, refreshToken,
                jwtTokenProvider.getAccessExpirationSeconds(), MemberResponse.from(member));
    }

    private String normalize(String email) {
        return email.trim().toLowerCase(Locale.ROOT);
    }
}
