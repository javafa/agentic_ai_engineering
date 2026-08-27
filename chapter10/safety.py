import ast
 
RISKY_ATTR = {                       # (모듈, 함수) 형태의 위험 호출
    ("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("os", "system"),
    ("shutil", "rmtree"), ("shutil", "move"),
    ("subprocess", "run"), ("subprocess", "Popen"), ("subprocess", "call"),
}
RISKY_METHODS = {"to_csv", "to_excel", "to_pickle", "to_parquet", "to_sql", "execute"}
# 외부 API를 사용하려면 requests를 허용 목록으로 빼거나 승인게이트를 거치도록 설계
RISKY_MODULES = {"subprocess", "socket", "shutil", "requests", "urllib"}
RISKY_BUILTINS = {"eval", "exec", "compile", "__import__"}
WRITE_MODES = {"w", "a", "x", "wb", "ab", "w+", "r+"}

def find_risky(code: str) -> list:
    """위험 요소 목록을 돌려준다. 비어 있으면 안전하다는 뜻."""
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues                # 문법 오류는 실행 단계의 자기수정에 맡긴다

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "open":
            # open(path, mode="w")처럼 키워드 인자로 준 모드는 잡지 못함
            mode = node.args[1].value if len(node.args) >= 2 \
                and isinstance(node.args[1], ast.Constant) else "r"
            if str(mode) in WRITE_MODES:
                issues.append(f"파일 쓰기: open(mode='{mode}')")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) \
                    and (node.func.value.id, node.func.attr) in RISKY_ATTR:
                issues.append(f"위험 호출: {node.func.value.id}.{node.func.attr}()")
            if node.func.attr in RISKY_METHODS:       # df.to_csv / con.execute(DML) 등
                issues.append(f"쓰기/부작용 호출: .{node.func.attr}()")
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in RISKY_MODULES:
                    issues.append(f"위험 모듈 import: {a.name}")
        if isinstance(node, ast.ImportFrom) and node.module \
                and node.module.split(".")[0] in RISKY_MODULES:
            issues.append(f"위험 모듈 import: {node.module}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in RISKY_BUILTINS:
            issues.append(f"위험 빌트인: {node.func.id}()")

    return sorted(set(issues))
