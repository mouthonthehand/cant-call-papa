"""
SQL 쿼리에서 테이블명, 컬럼명, 스키마(DB유저)명을 식별하여
임의의 별칭으로 치환하고, 역치환하는 모듈.
"""

import re
import string
import random

# Oracle SQL 키워드 (치환 대상에서 제외)
SQL_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "EXISTS",
    "BETWEEN", "LIKE", "IS", "NULL", "AS", "ON", "JOIN", "INNER",
    "LEFT", "RIGHT", "OUTER", "FULL", "CROSS", "NATURAL", "USING",
    "ORDER", "BY", "GROUP", "HAVING", "UNION", "ALL", "INTERSECT",
    "MINUS", "EXCEPT", "INSERT", "INTO", "VALUES", "UPDATE", "SET",
    "DELETE", "CREATE", "ALTER", "DROP", "TABLE", "VIEW", "INDEX",
    "SEQUENCE", "TRIGGER", "PROCEDURE", "FUNCTION", "PACKAGE",
    "BEGIN", "END", "IF", "THEN", "ELSE", "ELSIF", "CASE", "WHEN",
    "LOOP", "WHILE", "FOR", "EXIT", "RETURN", "DECLARE", "CURSOR",
    "OPEN", "FETCH", "CLOSE", "COMMIT", "ROLLBACK", "SAVEPOINT",
    "GRANT", "REVOKE", "WITH", "RECURSIVE", "DISTINCT", "UNIQUE",
    "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CONSTRAINT", "CHECK",
    "DEFAULT", "NOT", "ASC", "DESC", "NULLS", "FIRST", "LAST",
    "LIMIT", "OFFSET", "ROWNUM", "ROWID", "SYSDATE", "SYSTIMESTAMP",
    "DUAL", "LEVEL", "CONNECT", "START", "PRIOR", "NOCYCLE",
    "COUNT", "SUM", "AVG", "MIN", "MAX", "NVL", "NVL2", "DECODE",
    "TO_CHAR", "TO_DATE", "TO_NUMBER", "SUBSTR", "INSTR", "LENGTH",
    "TRIM", "LTRIM", "RTRIM", "UPPER", "LOWER", "REPLACE", "LPAD",
    "RPAD", "ROUND", "TRUNC", "MOD", "ABS", "CEIL", "FLOOR",
    "COALESCE", "GREATEST", "LEAST", "CAST", "EXTRACT", "OVER",
    "PARTITION", "ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD",
    "LISTAGG", "WITHIN", "RESPECT", "IGNORE", "ROWS", "RANGE",
    "UNBOUNDED", "PRECEDING", "FOLLOWING", "CURRENT", "ROW",
    "MERGE", "MATCHED", "SOURCE", "TARGET", "PIVOT", "UNPIVOT",
    "XMLAGG", "XMLELEMENT", "XMLFOREST", "XMLTYPE",
    "VARCHAR2", "NUMBER", "INTEGER", "DATE", "TIMESTAMP", "CLOB",
    "BLOB", "CHAR", "NVARCHAR2", "NCHAR", "FLOAT", "BINARY_FLOAT",
    "BINARY_DOUBLE", "RAW", "LONG", "BOOLEAN", "PLS_INTEGER",
    "EXCEPTION", "RAISE", "PRAGMA", "AUTONOMOUS_TRANSACTION",
    "BULK", "COLLECT", "FORALL", "SAVE", "EXCEPTIONS", "SQL",
    "SQLERRM", "SQLCODE", "FOUND", "NOTFOUND", "ISOPEN",
    "ROWCOUNT", "TYPE", "RECORD", "VARRAY", "NESTED",
    "OF", "REF", "OUT", "NOCOPY", "DETERMINISTIC", "PIPELINED",
    "PARALLEL_ENABLE", "RESULT_CACHE", "RELIES_ON",
    "DBMS_OUTPUT", "PUT_LINE", "UTL_FILE", "DBMS_LOB",
    "NO_DATA_FOUND", "TOO_MANY_ROWS", "DUP_VAL_ON_INDEX",
    "OTHERS", "WHEN", "THEN", "ELSE", "END",
    "MATERIALIZED", "SYNONYM", "PUBLIC", "REPLACE", "FORCE",
    "NOFORCE", "EDITIONABLE", "NONEDITIONABLE", "SHARING",
    "METADATA", "DATA", "NONE", "OBJECT", "UNDER",
    "STORAGE", "TABLESPACE", "LOGGING", "NOLOGGING",
    "COMPRESS", "NOCOMPRESS", "PARALLEL", "NOPARALLEL",
    "CACHE", "NOCACHE", "ENABLE", "DISABLE", "VALIDATE",
    "NOVALIDATE", "RELY", "NORELY", "IMMEDIATE", "DEFERRED",
    "INITIALLY", "DEFERRABLE", "BITMAP", "GLOBAL", "TEMPORARY",
    "PRESERVE", "TRUNCATE", "ANALYZE", "COMPUTE", "ESTIMATE",
    "STATISTICS", "EXPLAIN", "PLAN", "GATHER_PLAN_STATISTICS",
    "MONITOR", "NO_MONITOR", "HINT", "APPEND", "NOLOGGING",
    "PARALLEL", "LEADING", "USE_NL", "USE_HASH", "USE_MERGE",
    "ORDERED", "FIRST_ROWS", "ALL_ROWS", "RULE", "CHOOSE",
    "FULL", "INDEX", "INDEX_FFS", "INDEX_SS", "NO_INDEX",
    "HASH_AJ", "MERGE_AJ", "NL_AJ", "HASH_SJ", "MERGE_SJ", "NL_SJ",
    "PUSH_SUBQ", "NO_PUSH_SUBQ", "PUSH_PRED", "NO_PUSH_PRED",
    "UNNEST", "NO_UNNEST", "MATERIALIZE", "INLINE",
    "QB_NAME", "CARDINALITY", "OPT_PARAM", "DYNAMIC_SAMPLING",
    "RESULT_CACHE", "NO_RESULT_CACHE",
    "SIBLINGS",
    "ESCAPE", "ANY", "SOME", "EXISTS",
    "BULK", "COLLECT",
    "NEXTVAL", "CURRVAL",
    "NOTFOUND",
}


def _generate_alias(prefix: str, index: int) -> str:
    """접두어와 인덱스로 별칭 생성. 예: TBL_001, COL_003"""
    return f"{prefix}_{index:03d}"


def mask_query(sql: str) -> tuple[str, dict]:
    """
    SQL 쿼리에서 식별자를 마스킹한다.

    Returns:
        (마스킹된 쿼리, 매핑 딕셔너리)
        매핑: { 별칭 -> 원본 }
    """
    # 문자열 리터럴을 먼저 보호 (치환 대상에서 제외)
    string_literals = []
    def _save_string(m):
        string_literals.append(m.group(0))
        return f"__STR_{len(string_literals) - 1}__"

    protected = re.sub(r"'[^']*'", _save_string, sql)

    # 주석 보호
    comments = []
    def _save_comment(m):
        comments.append(m.group(0))
        return f"__CMT_{len(comments) - 1}__"

    protected = re.sub(r"--[^\n]*", _save_comment, protected)
    protected = re.sub(r"/\*[\s\S]*?\*/", _save_comment, protected)

    # 식별자 추출: schema.table.column 또는 schema.table 또는 단독 식별자
    # Oracle 식별자: 영문, 숫자, _, #, $ (첫 글자는 영문)
    identifier_pattern = r'\b([A-Za-z][A-Za-z0-9_#$]*(?:\.[A-Za-z][A-Za-z0-9_#$]*){1,2})\b'

    # 1단계: 점(.) 포함 식별자 (schema.table, schema.table.column)
    dotted_identifiers = set(re.findall(identifier_pattern, protected))

    # 2단계: 단독 식별자 (키워드 제외)
    single_pattern = r'\b([A-Za-z][A-Za-z0-9_#$]*)\b'
    all_words = set(re.findall(single_pattern, protected))

    # 키워드/보호 토큰 제외
    single_identifiers = {
        w for w in all_words
        if w.upper() not in SQL_KEYWORDS
        and not w.startswith("__STR_")
        and not w.startswith("__CMT_")
        and not re.match(r'^[0-9]', w)
    }

    # 매핑 생성
    mapping = {}  # alias -> original
    reverse = {}  # original -> alias

    # 점 포함 식별자의 각 파트를 분리하여 개별 매핑
    all_parts = set()
    for dotted in dotted_identifiers:
        parts = dotted.split(".")
        for part in parts:
            if part.upper() not in SQL_KEYWORDS:
                all_parts.add(part)

    # 단독 식별자도 포함
    all_parts.update(single_identifiers)

    # FROM/JOIN 뒤에 오는 "스키마.테이블 alias" 패턴에서 alias 식별
    # 예: FROM HR_ADMIN.TB_USER u  →  u 는 테이블alias
    table_alias_pattern = r'(?:FROM|JOIN)\s+\S+\s+([A-Za-z][A-Za-z0-9_#$]*)\b'
    table_aliases = set()
    for m in re.finditer(table_alias_pattern, protected, re.IGNORECASE):
        candidate = m.group(1)
        if candidate.upper() not in SQL_KEYWORDS:
            table_aliases.add(candidate)

    # 파트별 분류
    # - 점 표기 앞부분 중, 테이블alias가 아닌 것 = 스키마/유저
    # - 점 표기 뒤 = 테이블 또는 컬럼
    schema_parts = set()
    table_parts = set()
    dot_right_parts = set()  # 점 오른쪽에 나온 것들
    for dotted in dotted_identifiers:
        parts = dotted.split(".")
        if len(parts) == 3:
            schema_parts.add(parts[0])
            table_parts.add(parts[1])
            dot_right_parts.add(parts[2])
        elif len(parts) == 2:
            left, right = parts
            # 왼쪽이 테이블alias면 오른쪽은 컬럼
            if left in table_aliases:
                dot_right_parts.add(right)
            else:
                # 왼쪽은 스키마, 오른쪽은 테이블
                schema_parts.add(left)
                table_parts.add(right)

    # 별칭 부여
    sch_idx = 1
    tbl_idx = 1
    col_idx = 1
    alias_idx = 1

    # 길이가 긴 원본부터 치환 (부분 매칭 방지)
    sorted_parts = sorted(all_parts, key=lambda x: -len(x))

    for part in sorted_parts:
        if part in reverse:
            continue
        if part.upper() in SQL_KEYWORDS:
            continue

        if part in table_aliases:
            alias = _generate_alias("ALS", alias_idx)
            alias_idx += 1
        elif part in schema_parts:
            alias = _generate_alias("SCH", sch_idx)
            sch_idx += 1
        elif part in table_parts:
            alias = _generate_alias("TBL", tbl_idx)
            tbl_idx += 1
        else:
            alias = _generate_alias("COL", col_idx)
            col_idx += 1

        mapping[alias] = part
        reverse[part] = alias

    # 치환 수행 (긴 것부터, 단어 경계 매칭)
    result = protected
    for part in sorted_parts:
        if part not in reverse:
            continue
        alias = reverse[part]
        result = re.sub(r'\b' + re.escape(part) + r'\b', alias, result)

    # 문자열/주석 복원
    for i, cmt in enumerate(comments):
        result = result.replace(f"__CMT_{i}__", cmt)
    for i, s in enumerate(string_literals):
        result = result.replace(f"__STR_{i}__", s)

    return result, mapping


def unmask_query(masked_sql: str, mapping: dict) -> str:
    """
    마스킹된 쿼리를 원본 식별자로 복원한다.

    Args:
        masked_sql: 마스킹(또는 외부 LLM이 수정한) 쿼리
        mapping: { 별칭 -> 원본 } 딕셔너리
    """
    result = masked_sql
    # 긴 별칭부터 치환 (부분 매칭 방지)
    sorted_aliases = sorted(mapping.keys(), key=lambda x: -len(x))
    for alias, original in sorted((k, mapping[k]) for k in sorted_aliases):
        result = re.sub(r'\b' + re.escape(alias) + r'\b', original, result)
    return result
