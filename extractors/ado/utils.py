"""Utils for ADO."""
import functools
import time
import requests


def repeat_request(repeat_num=10):
    """Decorator that repeat requests in case of fails."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(repeat_num):
                try:
                    response = func(*args, **kwargs)
                    if 'Retry - After' in response.headers:
                        print(response.headers['Retry - After'])
                        time.sleep(120)
                        continue
                    break
                except requests.exceptions.ConnectionError:
                    time.sleep(60)
            else:
                print('Failed to reconnect.')
                raise requests.exceptions.ConnectionError
            return response
        return wrapper
    return decorator
