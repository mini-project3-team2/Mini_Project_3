package com.asknote.repository;

import com.asknote.entity.Member;
import java.util.Optional;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface MemberRepository extends JpaRepository<Member, Long> {

    Optional<Member> findByEmail(String email);

    Optional<Member> findByUuid(String uuid);

    /** 로그인용 — 행 잠금으로 동시 시도 시 실패 횟수가 누락되지 않게 한다 */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select m from Member m where m.email = :email")
    Optional<Member> findByEmailForUpdate(@Param("email") String email);

    boolean existsByEmail(String email);
}
