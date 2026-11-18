"""异步函数中跑耗时比较长的同步任务 丢到线程池中运行 """
import asyncio
import time
#
# def heavy_sync_work(n):  # 模型推理
#     print("同步阻塞开始")
#     time.sleep(2)
#     print("同步阻塞阻塞")
#     return n*n
#
# async def main():
#     # heavy_sync_work(10)
#     loop = asyncio.get_running_loop() # 拿到当前事件循环
#     # 在事件循环中运行同步函数  ,同步函数会创建一个线程池来运行
#     # parma1： 线程池句柄 parma2： 同步函数, param3: 函数参数
#     result = await  loop.run_in_executor(None,heavy_sync_work,10) # 让出cpu
#     print("结果：",result)

# asyncio.run(main())


# CPU密集任务，不是sleep！这个会持续占用CPU，GIL不会释放



#
# async def cpu_task(name: str):
#     print(f"【{name}】开始计算")
#     s = 0
#     time.sleep(10)
#     # await asyncio.sleep(10)
#
#     print(f"【{name}】计算结束，sum={s}")
#     return s
#
# async def main():
#
#     # 两个任务丢进默认线程池 ThreadPoolExecutor
#     t1 = cpu_task('a')
#     t2 = cpu_task('b')
#
#     print("开始等待两个cpu任务...")
#     await asyncio.gather(t1, t2)
#     print("全部完成")
#
# if __name__ == "__main__":
#     start = time.time()
#     asyncio.run(main())
#     print(f"总耗时：{time.time() - start:.2f} s")





"""异步函数如何实现并发"""

# async  def fetch(name,sec):
#     print(f"开始 {name}")
#     # time.sleep(sec)
#     await asyncio.sleep(sec)
#     print(f"完成 {name}")
#     return f"{name} 的结果"
#
# async def main():
#
#    # await  fetch("请求A",2)
#    # await  fetch("请求B", 2)
#    # await  fetch("请求C", 2)
#
#    results = await asyncio.gather(
#        fetch("请求A", 2),
#        fetch("请求B", 2),
#        fetch("请求C", 2)
#    )
#    print(results)
#
# asyncio.run(main())

# import asyncio
# # 模块级集合：持有所有后台任务的强引用，防止被 GC 提前回收
# _background_tasks: set[asyncio.Task] = set()
#
# async def grade_exam(exam_id):
#     print(f"开始批改试卷 {exam_id}……")
#     await asyncio.sleep(2)               # 模拟耗时的批改过程
#     print(f"试卷 {exam_id} 批改完成")
#
# async def submit():
#     task = asyncio.create_task(grade_exam("EX-001"))  # 丢到后台
#     _background_tasks.add(task)                         # 关键①：强引用，防 GC
#     # _background_tasks.discard 集合移除对象的函数
#     # 任务执行完成之后会自动进入到_background_tasks.discard函数去，参数为该任务的句柄  _background_tasks.discard(task)
#     task.add_done_callback(_background_tasks.discard)   # 关键②：跑完自动移除
#     print("接口立即返回：已收到，正在后台批改")
#
# async def main():
#     await submit() # 不耗时任务
#     await asyncio.sleep(3)    # 模拟服务持续运行，给后台任务跑完的时间
#     print("当前后台任务数：", len(_background_tasks))
# #
# asyncio.run(main())
#
# s1 = {12,34,63}
# print(s1)
# s1.discard(34)
# print(s1)

# 如何自定义一个上下文管理器
from contextlib import contextmanager,asynccontextmanager
# 如何实现一个同步的上下文管理器
# @contextmanager
# def my_open():
#     """业务逻辑编写处"""
#     print("【准备】打开文件资源成功，返回文件对象")    # 进入 with 时执行
#     yield "文件对象"              # 把 yield 的值交给 as 后面的变量
#     """资源回收的代码"""
#     #  "文件对象".close
#     print("【收尾】自动回收")      # 离开 with 时执行
#
# with my_open() as res:
#     print(f"正在使用：{res}")
#     print("文件操作完成")

# 如何实现一个异步的上下文管理器
# @asynccontextmanager
# async def my_open():
#     """业务逻辑编写处"""
#     print("【准备】打开文件资源成功，返回文件对象")    # 进入 with 时执行
#     yield "文件对象"              # 把 yield 的值交给 as 后面的变量
#     """资源回收的代码"""
#     #  "文件对象".close
#     print("【收尾】自动回收")      # 离开 with 时执行
#
#
# async def main():
#     async with my_open() as res:
#         print(f"正在使用：{res}")
#         print("文件操作完成")
#
# asyncio.run(main())