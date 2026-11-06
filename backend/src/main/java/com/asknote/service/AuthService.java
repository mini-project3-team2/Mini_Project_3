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
import java.time.temporal.ChronoUnit;
import java.util.Map;
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

    @Value("${auth.login.max-attempts}")
    private int maxAttempts;

    @Value("${auth.login.lock-minutes}")
    private long lockMinutes;

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
     * Brute Force 조치: 연속 실패 maxAttempts 회 → lockMinutes 분 잠금 (423, 잠금 중에는 올바른 비밀번호도 거부)
     * 실패 횟수는 예외를 던져도 저장돼야 하므로 BusinessException 에서 롤백하지 않는다
     */
    @Transactional(noRollbackFor = BusinessException.class)
    public TokenResponse login(LoginRequest request, String ip) {
        String email = normalize(request.email());
        Member member = memberRepository.findByEmailForUpdate(email).orElse(null);
        if (member == null) {
            auditLogger.loginFailure(email, ip);
            throw new BusinessException(ErrorCode.INVALID_CREDENTIALS);
        }

        LocalDateTime now = LocalDateTime.now();
        if (member.isLocked(now)) {
            auditLogger.accountLocked(email, ip);
            throw locked(member);
        }
        if (member.getLockedUntil() != null) {
            member.resetLoginFailure(); // 잠금 시간이 지났으면 횟수를 처음부터 다시 센다
        }

        if (!passwordEncoder.matches(request.password(), member.getPassword())) {
            member.recordLoginFailure(maxAttempts, now.plusMinutes(lockMinutes));
            if (member.isLocked(now)) {
                auditLogger.accountLocked(email, ip);
                throw locked(member);
            }
            auditLogger.loginFailure(email, ip);
            throw new BusinessException(ErrorCode.INVALID_CREDENTIALS);
        }

        member.resetLoginFailure();
        auditLogger.loginSuccess(email, ip);
        return issueTokens(member);
    }

    private BusinessException locked(Member member) {
        return new BusinessException(ErrorCode.ACCOUNT_LOCKED,
                Map.of("lockedUntil", member.getLockedUntil().truncatedTo(ChronoUnit.SECONDS)));
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
