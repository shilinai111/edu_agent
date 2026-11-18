"""
    装饰器： 在不修改原函数情况下，给函数增加功能
"""
import time
# 无参装饰器模板
from functools import  wraps
def outer(func):
    @wraps(func) # 保留原函数的元信息,不加也可以
    def warpper(*args,**kwargs):
        # 函数加功能的地方
        ret = func(*args, **kwargs)
        # 函数加功能的地方
        return ret
    return warpper
# 需要给函数额外添加功能时，通过装饰器实现
# 实现方法：   1、调出装饰器模板  2、在模板中实现要装饰功能的业务逻辑
#            3、装饰要添加功能的函数
# 要实现记录函数耗费时间的功能
from functools import  wraps
def outer(func):
    @wraps(func)
    def warpper(*args,**kwargs):
        # 函数加功能的地方
        ntime = time.time()
        ret = func(*args, **kwargs)
        print("程序的花费时间:", time.time() - ntime)
        # 函数加功能的地方
        return ret
    return warpper
@outer
def pay(): # func = pay, pay = wraper
    """支付接口"""
    time.sleep(2)
    print("用户支付成功")

pay()
