from selenium import webdriver
import re

# 启动浏览器
driver = webdriver.Chrome()

# 打开一个页面
driver.get('http://xhslink.com/C/AHPEex')

# 获取当前页面的 URL
current_url = driver.current_url
print('链接是：')
print('aaa' + current_url)

############################################## 解析 ###########################################################
# 正则表达式模式
pattern = r"/explore/([a-zA-Z0-9]+)"

# 使用 search 方法查找匹配项
match = re.search(pattern, current_url)

# 如果找到匹配项，则提取并打印
if match:
    extracted_string = match.group(1)
    print('目标是：')
    print(extracted_string)
else:
    print("No match found")

# 关闭浏览器
driver.quit()