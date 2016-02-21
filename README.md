# overloader
*Function / Method overloading done right.*

**overloader** is a Python library to make function and method overloading easier and safer. Whereas traditional
methods forces the usage of `**kwargs` or default arguments, and requires lots of boilerplate code for checking;
**overloader** can automize the job with a much cleaner and intuitive interface.

Some people might function overloading *unpythonic*: I'm not going to argue to change their minds, nor will try to come
up with scenarios or reasons why **overload** might be useful. The main reason why I created it is to play with
*typing* module in Python 3.5, and see what I can do with it. If you find it useful, that's great!

## Usage
To use **overloader**, simply use `@overload` decorator, and everything should work exactly as you might expect:

```python
import typing
from overloader import overload

@overload
def simple_func(a, b):
    return "First simple_func"

@overload
def simple_func(a, b, c, d=32, *, ka, dka="default"):
    return "Second simple_func"

print(simple_func(3, 14))
print(simple_func(3, 14, 15, ka="pi"))

@overload
def typed_func(a: typing.Union[int, float], d: typing.Dict[int, int]):
    return "First typed_func"

@overload
def typed_func(a: int, b: typing.Dict[int, str]):
    return "Second typed_func"

print(typed_func(2, {71: 82}))
print(typed_func(2, {71: "a string"}))

"""
Works for normal methods and staticmethods as well.
"""
class C:
    @classmethod
    @overload
    def class_method(cls, a: str, b: int):
        return "First class_method"
        
    @classmethod
    @overload
    def class_method(cls, a: str, b: float):
        return "Second class_method"
        
c = C()
print(c.class_method("pi", 3))
print(c.class_method("e", 2.7182))
```
    
A few key-point to keep in mind while using **overloader**:

* **overloader** is still under heavy development. **Bugs are expected and behaviour might change.**
* **overloader** doesn't choose the *most specific* typing definition. For instance:

      ```python
      @overload
      def f(a: int):
        return "int!"
        
      @overload
      def f(a: typing.Any):
        return "any!"
        
      print(f(5))
      ```
      
  You might expect **overloader** to call the first definition, since it's more specific (`int`, instead of *any*), but
  **overloader** doesn't do that, and it will complain that there are multiple alternatives that satisfy the given
  arguments (Exception `AmbiguousMethods` will be raised).
  
  This behaviour is due to my laziness, and I think it's more complicated than it seems. If you can come up with a
  solution that handles complex type hints as well, I would love to merge!
* Any decorator, including `@classmethod` and `@staticmethod`, must come **before** `@overload`.

## Installing
    pip3 install overloader

or manually clone the repository and install:

    git clone https://github.com/boramalper/overloader.git
    cd overloader
    sudo python3 setup.py install

## Contributing
* Add support for all the possible type hints that are defined by `typing` module.
* Code cleanup and general improvements
    
## License
MIT License. See the [LICENSE](/LICENSE) file for details.
