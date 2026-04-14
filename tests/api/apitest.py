import os
import time

from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
)

start_time = time.time()
first_token_time = None

# 初始化变量记录消耗
total_tokens = 0
prompt_tokens = 0
completion_tokens = 0

messages = [{"role": "user", "content": "不需要任何过程，告诉我1+1的结果是多少？"}]

completion = client.chat.completions.create(
    model="qwen3-4b",  # 您可以按需更换为其它深度思考模型
    messages=messages,
    extra_body={"enable_thinking": False},  # 开启思考过程并包含使用统计
    stream=True,
    stream_options = {"include_usage": True}  # 在流式过程中包含使用统计信息
)

is_answering = False  # 是否进入回复阶段
print("\n" + "=" * 20 + "思考过程" + "=" * 20)

for chunk in completion:
    # 🔥 修复 2: 先检查 choices 是否非空，避免 IndexError
    if not chunk.choices:
        # 空 choices 通常是流结束信号，可能包含 usage 信息，继续处理下方 usage 逻辑
        pass
    else:
        # 🔥 修复 3: 只在有内容时才记录 TTFT（避免空 chunk 误触发）
        if first_token_time is None and (
            (hasattr(chunk.choices[0].delta, "reasoning_content") and chunk.choices[0].delta.reasoning_content) or
            (hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content)
        ):
            first_token_time = time.time()
        
        # 🔥 修复 4: 安全访问 delta（确保 choices[0] 存在后再访问）
        delta = chunk.choices[0].delta
        
        # 处理思考过程
        if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
            if not is_answering:
                print(delta.reasoning_content, end="", flush=True)
        
        # 处理正式回复
        if hasattr(delta, "content") and delta.content:
            if not is_answering:
                print("\n" + "=" * 20 + "完整回复" + "=" * 20)
                is_answering = True
            print(delta.content, end="", flush=True)

    # 🔥 修复 5: usage 信息通常在最后一个空 choices 的 chunk 中，独立处理
    if hasattr(chunk, 'usage') and chunk.usage is not None:
        # print(f"\n\n[用量统计] {chunk.usage}")
        prompt_tokens = chunk.usage.prompt_tokens
        completion_tokens = chunk.usage.completion_tokens
        total_tokens = chunk.usage.total_tokens

# 记录总耗时
total_duration = time.time() - start_time
ttft_duration = first_token_time - start_time if first_token_time else 0

print(f"\n\n" + "=" * 48)
print(f"统计信息:")
print(f"- 网络往返延迟 (TTFT): {ttft_duration:.2f}s")
print(f"- 总任务执行耗时: {total_duration:.2f}s")
print("=" * 48)

# 在循环结束后打印
print(f"\n\n" + "=" * 48)
print(f"Token 消耗统计:")
print(f"- Prompt Tokens: {prompt_tokens}")
print(f"- Completion Tokens: {completion_tokens}")
print(f"- Total Tokens: {total_tokens}")
print(f"- 总任务执行耗时: {total_duration:.2f}s")
print("=" * 48)
