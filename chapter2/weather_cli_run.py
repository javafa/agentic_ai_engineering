import subprocess

# 에이전트에게 주는 Tool은 단 하나 — "쉘 명령을 실행한다"
def run_shell(command: str) -> str:
    """쉘 명령을 실행하고 출력(stdout/stderr)을 돌려준다."""
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=30
    )
    return result.stdout or result.stderr

tools = [{
    'name': 'run_shell',
    'description': '쉘 명령을 실행한다. 예: python weather_cli.py Seoul',
    'input_schema': {
        'type': 'object',
        'properties': {
            'command': {'type': 'string', 'description': '실행할 쉘 명령'}
        },
        'required': ['command'],
    },
}]
