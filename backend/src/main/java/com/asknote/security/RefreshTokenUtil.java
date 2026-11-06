package com.asknote.security;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;

/**
 * Refresh 토큰 — JWT 가 아닌 무작위 문자열, DB 에는 SHA-256 해시만 저장 (원문 저장 안 함)
 */
public final class RefreshTokenUtil {

    private static final SecureRandom RANDOM = new SecureRandom();

    private RefreshTokenUtil() {
    }

    /** 32바이트 무작위 값 (Base64 URL-safe) */
    public static String generate() {
        byte[] bytes = new byte[32];
        RANDOM.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    /** SHA-256 해시 (hex 64자 → refresh_tokens.token_hash) */
    public static String hash(String token) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(token.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
