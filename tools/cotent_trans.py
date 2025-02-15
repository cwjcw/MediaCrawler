import pandas as pd
import jdy
import asyncio


# 读取数据
file_path = r'G:\New Code\XHS_Spider\MediaCrawler\data\xhs/5_search_contents_2025-02-13.csv'
data = pd.read_csv(file_path)

# 字段重命名
data.rename(columns={
    'note_id': '笔记ID',
    'type': '笔记类别',
    'title': '笔记标题',
    'desc': '笔记正文',
    'video_url': '视频链接',
    'time': '发布时间',
    'last_update_time': '最后更新时间',
    'user_id': '用户ID',
    'nickname': '用户昵称',
    'avatar': '头像链接',
    'liked_count': '点赞数',
    'collected_count': '收藏数',
    'comment_count': '评论数',
    'share_count': '转发数',
    'ip_location': '所在省份',
    'image_list': '封面链接',
    'tag_list': '标签明细',
    'last_modify_ts': '最后修改时间',
    'note_url': '笔记链接',
    'source_keyword': '关键词',
    'xsec_token': 'xsec_token'
}, inplace=True)

# 时间戳转换为日期
data['发布时间'] = pd.to_datetime(data['发布时间'], unit='ms')
data['最后更新时间'] = pd.to_datetime(data['最后更新时间'], unit='ms')
data['最后修改时间'] = pd.to_datetime(data['最后修改时间'], unit='ms')

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

data['点赞数'] = data['点赞数'].apply(convert_like_count)
data['收藏数'] = data['收藏数'].apply(convert_like_count)
data['评论数'] = data['评论数'].apply(convert_like_count)
data['转发数'] = data['转发数'].apply(convert_like_count)

# 保存转换后的数据为新的CSV文件
output_file_path = r'G:\New Code\XHS_Spider\MediaCrawler\data\xhs/content.csv'
data.to_csv(output_file_path, index=False, encoding='utf-8-sig')

# 显示转换后的数据
print(data.head())

####################################以下是执行简道云上传################################################
jdy = jdy.JDY()

# 调用并发库asyncio执行批量上传
async def main():
    appId= "67b019c13a7604cb335160a2"
    entryId= "67b01bfe486a68d4634c79cc"
    await jdy.batch_create(app_id=appId, entry_id=entryId, source_data=data)
    print('全部上传成功')
asyncio.run(main())


