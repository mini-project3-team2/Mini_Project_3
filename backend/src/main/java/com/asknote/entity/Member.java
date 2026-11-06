package com.asknote.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import java.util.UUID;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "members")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Member {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 외부 식별자. JWT subject, Chroma 소유자 필터 값 */
    @Column(name = "uuid", nullable = false, unique = true, length = 36, columnDefinition = "char(36)")
    private String uuid;

    @Column(name = "email", nullable = false, unique = true, length = 100)
    private String email;

    /** BCrypt 해시 */
    @Column(name = "password", nullable = false)
    private String password;

    @Enumerated(EnumType.STRING)
    @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "role", nullable = false, length = 20)
    private Role role;

    @Column(name = "failed_login_count", nullable = false)
    private int failedLoginCount;

    @Column(name = "locked_until")
    private LocalDateTime lockedUntil;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    private Member(String email, String encodedPassword, Role role) {
        this.uuid = UUID.randomUUID().toString();
        this.email = email;
        this.password = encodedPassword;
        this.role = role;
        this.failedLoginCount = 0;
    }

    /** 회원가입용. 역할은 항상 MEMBER (요청으로 받지 않음) */
    public static Member createMember(String email, String encodedPassword) {
        return new Member(email, encodedPassword, Role.MEMBER);
    }

    /** 환경 변수로 관리자 계정을 만들 때만 사용 */
    public static Member createAdmin(String email, String encodedPassword) {
        return new Member(email, encodedPassword, Role.ADMIN);
    }

    public boolean isLocked(LocalDateTime now) {
        return lockedUntil != null && lockedUntil.isAfter(now);
    }

    /** 로그인 실패 1회 기록. 기준 횟수에 도달하면 잠금 시각을 설정한다 */
    public void recordLoginFailure(int maxAttempts, LocalDateTime lockUntil) {
        this.failedLoginCount++;
        if (this.failedLoginCount >= maxAttempts) {
            this.lockedUntil = lockUntil;
        }
    }

    /** 로그인 성공 시 실패 횟수 · 잠금 초기화 */
    public void resetLoginFailure() {
        this.failedLoginCount = 0;
        this.lockedUntil = null;
    }
}
