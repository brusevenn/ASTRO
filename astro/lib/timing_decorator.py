import time


def timing_decorator_print(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"{func.__name__}     : {execution_time}  ")
        return result
    return wrapper

def timing_decorator_return(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)  #      
        end_time = time.time()
        execution_time = end_time - start_time  #       
        return result, execution_time  #             
    return wrapper

if __name__ == "__main__":
    @timing_decorator_return
    def my_function():
        pass

    result, result_time = my_function()
    print(result, result_time)
    print(f"type： {result}")