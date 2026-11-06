package com.asknote.repository;

import com.asknote.entity.Document;
import com.asknote.entity.DocumentStatus;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface DocumentRepository extends JpaRepository<Document, Long> {

    /** 내 자료 목록 (최신순, 페이징 없음) */
    List<Document> findByMemberIdOrderByCreatedAtDesc(Long memberId);

    /** 질문 시 AI 에 넘길 READY 문서 id 목록 */
    @Query("select d.id from Document d where d.member.id = :memberId and d.status = :status")
    List<Long> findIdsByMemberIdAndStatus(@Param("memberId") Long memberId, @Param("status") DocumentStatus status);
}
