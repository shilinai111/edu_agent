# scripts/manual_tests/create_test_exam_docx.py
"""生成一份包含客观题+简答题的测试 Word 文件"""

import sys
sys.path.insert(0, ".")
from docx import Document

doc = Document()

# 第1题：单选题
doc.add_paragraph("第1题 下列关于 Java 中 final 关键字的说法，正确的是（ ）")
doc.add_paragraph("A. final 修饰的变量不能重新赋值")
doc.add_paragraph("B. final 修饰的方法不能被继承")
doc.add_paragraph("C. final 修饰的类可以被继承")
doc.add_paragraph("D. final 修饰的方法可以被重写")
doc.add_paragraph("答：A")
doc.add_paragraph("")

# 第2题：多选题
doc.add_paragraph("第2题 下列说法正确的是（多选）")
doc.add_paragraph("A. ArrayList 底层是数组")
doc.add_paragraph("B. LinkedList 支持随机访问")
doc.add_paragraph("C. HashMap 允许 null key")
doc.add_paragraph("D. HashSet 不允许重复元素")
doc.add_paragraph("答：ACD")
doc.add_paragraph("")

# 第3题：简答题
doc.add_paragraph("第3题 请解释 Spring IOC 的概念及其核心作用。")
doc.add_paragraph("答：")
doc.add_paragraph("Spring IOC（控制反转）是一种设计思想，将对象的创建和依赖关系的管理从程序代码中抽离出来，交给 Spring 容器统一管理。")
doc.add_paragraph("核心作用是解耦：业务代码不再主动创建对象，而是由容器注入所需依赖，降低了模块间的耦合度，便于单元测试和维护。")
doc.add_paragraph("")

# 第4题：判断题
doc.add_paragraph("第4题 Java 中 int 类型的默认值是 0。（判断）")
doc.add_paragraph("答：正确")

doc.save("test_exam_answer.docx")
print("测试文件已生成：scripts/manual_tests/test_exam_answer.docx")
