import pandas as pd
import jdy
import asyncio


# 读取上传的CSV文件
file_path = r'G:\New Code\XHS_Spider\MediaCrawler\data\xhs/8_search_comments_2025-02-14.csv'
df = pd.read_csv(file_path)

# 标题转换
df.rename(columns={
    'comment_id': '评论ID',
    'create_time': '评论时间',
    'ip_location': '定位',
    'note_id': '笔记ID',
    'content': '评论内容',
    'user_id': '用户ID',
    'nickname': '用户名称',
    'avatar': '头像链接',
    'sub_comment_count': '子评论数量',
    'pictures': '图片链接',
    'parent_comment_id': 'parent_comment_id',
    'last_modify_ts': '最后更新时间',
    'like_count': '点赞数量'
}, inplace=True)


# 时间字段转换
df['评论时间'] = pd.to_datetime(df['评论时间'], unit='ms')
df['最后更新时间'] = pd.to_datetime(df['最后更新时间'], unit='ms')

# 转换数量（处理类似“4.9万”和“1千+”这种格式）
def convert_like_count(value):
    if isinstance(value, str):
        # 处理“万”的情况
        if '万' in value:
            try:
                return float(value.replace('万', '')) * 10000
            except ValueError:
                return None  # 如果转换失败，返回None
        # 处理“千+”的情况
        elif '千' in value:
            try:
                return float(value.replace('千', '')) * 1000
            except ValueError:
                return None  # 如果转换失败，返回None
        # 处理其他可能的字符串（例如含有“+”）
        elif '+' in value:
            try:
                return float(value.replace('+', ''))
            except ValueError:
                return None
    return value

df['点赞数量'] = df['点赞数量'].apply(convert_like_count)
df['子评论数量'] = df['子评论数量'].apply(convert_like_count)

# 显示前几行数据以确认转换结果
print(df.head())

# 如果需要保存转换后的数据，可以使用以下代码：
df.to_csv(r'G:\New Code\XHS_Spider\MediaCrawler\data\xhs/converted_comments.csv', index=False, encoding='utf-8-sig')

####################################以下是执行简道云上传################################################
jdy = jdy.JDY()

# 调用并发库asyncio执行批量上传
async def main():
    appId= "67b019c13a7604cb335160a2"
    entryId= "67b02d101a620bee3904dc21"
    await jdy.batch_create(app_id=appId, entry_id=entryId, source_data=df)
    print('全部上传成功')
asyncio.run(main())