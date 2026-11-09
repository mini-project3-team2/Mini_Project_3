package com.asknote.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.Optional;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Access 토큰 발급 · 검증
 * - subject = 회원 uuid (내부 id 는 토큰에 넣지 않음), claim "role"
 * - 서명 HS256, 키는 환경 변수 JWT_SECRET (32바이트 이상)
 */
@Component
public class JwtTokenProvider {

    private static final String ROLE_CLAIM = "role";

    private final SecretKey key;
    private final long accessExpirationMillis;

    public JwtTokenProvider(
            @Value("${jwt.secret}") String secret,
            @Value("${jwt.access-expiration}") long accessExpirationMillis) {
        byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
        if (bytes.length < 32) {
            throw new IllegalStateException("JWT_SECRET 은 32바이트 이상이어야 합니다");
        }
        this.key = Keys.hmacShaKeyFor(bytes);
        this.accessExpirationMillis = accessExpirationMillis;
    }

    public String createAccessToken(String uuid, String role) {
        Date now = new Date();
        return Jwts.builder()
                .subject(uuid)
                .claim(ROLE_CLAIM, role)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + accessExpirationMillis))
                .signWith(key)
                .compact();
    }

    /** 유효한 토큰이면 Claims, 만료 · 위조 · 형식 오류면 빈 값 */
    public Optional<Claims> parse(String token) {
        try {
            return Optional.of(Jwts.parser().verifyWith(key).build()
                    .parseSignedClaims(token).getPayload());
        } catch (JwtException | IllegalArgumentException e) {
            return Optional.empty();
        }
    }

    public String getRole(Claims claims) {
        return claims.get(ROLE_CLAIM, String.class);
    }

    /** 응답의 expiresIn (초) */
    public long getAccessExpirationSeconds() {
        return accessExpirationMillis / 1000;
    }
}
