package com.asknote.repository;

import com.asknote.entity.Member;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MemberRepository extends JpaRepository<Member, Long> {

    Optional<Member> findByEmail(String email);

    Optional<Member> findByUuid(String uuid);

    boolean existsByEmail(String email);
}
