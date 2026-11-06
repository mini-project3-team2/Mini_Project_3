package com.asknote.repository;

import com.asknote.entity.Document;
import com.asknote.entity.DocumentStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface DocumentRepository extends JpaRepository<Document, Long> {

    /** 내 자료 목록 (최신순, 페이징 없음) */
    List<Document> findByMemberIdOrderByCreatedAtDesc(Long memberId);

    /** 질문 시 AI 에 넘길 READY 문서 id 목록 */
    @Query("select d.id from Document d where d.member.id = :memberId and d.status = :status")
    List<Long> findIdsByMemberIdAndStatus(@Param("memberId") Long memberId, @Param("status") DocumentStatus status);

    /** 삭제용 — 소유자(uuid)까지 함께 조회 (open-in-view 꺼짐 → 지연 로딩 대신 fetch join) */
    @Query("select d from Document d join fetch d.member where d.id = :id")
    Optional<Document> findWithMemberById(@Param("id") Long id);
}
