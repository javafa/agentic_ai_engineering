# 에이전트(Client)가 Server에 연결하기
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server = StdioServerParameters(command='python', args=['weather_mcp_server.py'])

async def main():
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Server가 제공하는 Tool 목록을 자동으로 받아온다
            tools = await session.list_tools()
            print([t.name for t in tools.tools])   # ['get_weather']

            # 2. 이름과 인자만 넘겨 Tool을 호출한다
            result = await session.call_tool('get_weather', {'city': 'Seoul'})
            print(result.content[0].text)

asyncio.run(main())
