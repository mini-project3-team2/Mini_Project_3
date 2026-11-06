package com.asknote.service;

import com.asknote.common.audit.AuditLogger;
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
import java.util.Optional;
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
    private final AuditLogger auditLogger;

    @Value("${jwt.refresh-expiration}")
    private long refreshExpirationMillis;

    @Transactional
    public MemberResponse signup(SignupRequest request, String ip) {
        String email = normalize(request.email());
        if (memberRepository.existsByEmail(email)) {
            throw new BusinessException(ErrorCode.DUPLICATE_EMAIL);
        }
        Member member = Member.createMember(email, passwordEncoder.encode(request.password()));
        memberRepository.save(member);
        auditLogger.signup(email, ip);
        return MemberResponse.from(member);
    }

    /**
     * 로그인 — 이메일이 없든 비밀번호가 틀리든 같은 401 (이메일 존재 여부를 알려주지 않음)
     * TODO(Brute Force 조치): 현재는 실패 횟수 제한이 없음 → 취약점 재현 캡처 후 fix(security) 커밋에서 잠금 추가
     */
    @Transactional
    public TokenResponse login(LoginRequest request, String ip) {
        String email = normalize(request.email());
        Optional<Member> found = memberRepository.findByEmail(email)
                .filter(m -> passwordEncoder.matches(request.password(), m.getPassword()));
        if (found.isEmpty()) {
            auditLogger.loginFailure(email, ip);
            throw new BusinessException(ErrorCode.INVALID_CREDENTIALS);
        }
        auditLogger.loginSuccess(email, ip);
        return issueTokens(found.get());
    }

    /** 재발급(회전) — 기존 Refresh 행 삭제 → 새 Access · Refresh 발급 */
    @Transactional
    public TokenResponse refresh(String refreshToken, String ip) {
        RefreshToken saved = refreshTokenRepository.findByTokenHash(RefreshTokenUtil.hash(refreshToken))
                .orElseThrow(() -> {
                    auditLogger.refreshFailure(ip);
                    return new BusinessException(ErrorCode.INVALID_REFRESH_TOKEN);
                });
        refreshTokenRepository.delete(saved);
        if (saved.isExpired(LocalDateTime.now())) {
            auditLogger.refreshFailure(ip);
            throw new BusinessException(ErrorCode.INVALID_REFRESH_TOKEN);
        }
        return issueTokens(saved.getMember());
    }

    /** 로그아웃 — 로그인한 본인의 Refresh 만 삭제 (없거나 남의 토큰이면 아무것도 하지 않음) */
    @Transactional
    public void logout(Member member, String refreshToken, String ip) {
        refreshTokenRepository.findByTokenHash(RefreshTokenUtil.hash(refreshToken))
                .filter(t -> t.getMember().getId().equals(member.getId()))
                .ifPresent(refreshTokenRepository::delete);
        auditLogger.logout(member.getEmail(), ip);
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
