import re

with open("jcia/adapters/ai/openai_adapter.py", "r", encoding="utf-8") as f:
    content = f.read()

# 修复 tokens_used 计算的语法错误
# 问题: tokens_used=sum(...) 应该改为计算tokens_used
old_code = """            tokens_used=sum(
                self.generate_tests(
                    TestGenerationRequest(
                        target_classes=[s["class_name"]],
                        code_snippets={s["class_name"]: s["code"]},
                    ),
                    project_path,
                    **kwargs,
                ).tokens_used
                for s in uncovered_segments[:1]  # 只估算第一个
            )
        )"""

new_code = """            # 计算tokens_used
            tokens_used = 0
            if uncovered_segments:
                # 简化处理，使用第一个片段估算
                first_segment = uncovered_segments[0]
                test_gen_result = self.generate_tests(
                    TestGenerationRequest(
                        target_classes=[first_segment["class_name"]],
                        code_snippets={first_segment["class_name"]: first_segment["code"]},
                    ),
                    project_path,
                    **kwargs,
                )
                tokens_used = test_gen_result.tokens_used"""

content = content.replace(old_code, new_code)

with open("jcia/adapters/ai/openai_adapter.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed openai_adapter.py")
