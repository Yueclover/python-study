"""
第 2 周 Day 8 — 类与对象（对照 JS class，但 self 要手写）

运行：python week02\\day08_class.py
"""

# ============================================================
# 1. 定义类 —— __init__ 就是 constructor，self 就是 this
# ============================================================
class User:
    def __init__(self, name, age):      # 对应 constructor(name, age)
        self.name = name                # 对应 this.name = name
        self.age = age

    def greet(self):                    # 每个方法第一个参数必须是 self
        return f"我是 {self.name}，{self.age} 岁"


u = User("小明", 28)                    # 创建实例，不用 new！
print(u.name)
print(u.greet())

# 👉 试一试：再创建一个 User，调用它的 greet()
class User:
    def __init__(self,name, gender):
        self.name = name
        self.gender = gender

    def great(self):
        print(f"我叫{self.name},{self.gender}孩子")
u = User("小明","男")
print(u.great())

# ============================================================
# 2. 类属性 vs 实例属性
# ============================================================
class Counter:
    species = "计数器"          # 类属性，所有实例共享（对应 static）

    def __init__(self):
        self.count = 0          # 实例属性，每个对象独立

    def increment(self):
        self.count += 1
        return self.count


c = Counter()
c.increment()
c.increment()
print(c.count)                  # 2
print(Counter.species)          # 计数器


# ============================================================
# 3. 继承 —— class 子类(父类)
# ============================================================
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return "某种叫声"


class Dog(Animal):              # 对应 class Dog extends Animal
    def __init__(self, name, breed):
        super().__init__(name)  # 对应 super(name)
        self.breed = breed

    def speak(self):            # 方法重写 override
        return "汪汪"


d = Dog("旺财", "柴犬")
print(d.name, d.breed, d.speak())

# 👉 试一试：再写一个 Cat(Animal)，speak() 返回 "喵"
class Cat(Animal):
   def __init__(self, name):
        super().__init__(name)
        self.breed = "猫科"

    def speak(self):
        return "喵喵"

# ============================================================
# 4. 常用魔术方法 __dunder__（JS 没有这么系统的机制）
# ============================================================
class Money:
    def __init__(self, amount):
        self.amount = amount

    def __str__(self):                  # 对应 toString()，print 时调用
        return f"￥{self.amount}"

    def __repr__(self):                 # 调试/控制台显示用
        return f"Money({self.amount})"

    def __add__(self, other):           # 让对象支持 + 运算符（运算符重载）
        return Money(self.amount + other.amount)

    def __eq__(self, other):            # 让对象支持 == 比较
        return self.amount == other.amount


m1 = Money(100)
m2 = Money(50)
print(m1)                # ￥100  （触发 __str__）
print(m1 + m2)          # ￥150  （触发 __add__）
print(m1 == Money(100)) # True  （触发 __eq__）

# 👉 试一试：给 Money 加一个 __sub__ 方法支持减法


# ============================================================
# 5. @property —— 把方法当属性访问（对应 JS 的 get）
# ============================================================
class Circle:
    def __init__(self, radius):
        self.radius = radius

    @property
    def area(self):                     # 对应 get area()
        return 3.14159 * self.radius ** 2


circle = Circle(5)
print(circle.area)      # 78.53975  注意：没有括号！像属性一样访问

# 👉 试一试：给 Circle 加一个 @property 算周长 perimeter


print("\n[完成] Day 8 跑通了！去 ROADMAP.md 勾掉 Day 8。")
