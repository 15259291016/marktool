"""marktool URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.views.generic.base import TemplateView
from django.urls import path
from marktool.src.mark_tools.mark import *
from marktool.src.mark_tools.query import *
from marktool.src.mark_tools.faq import *
from marktool.src.mark_tools.user import *
from marktool.src.mark_tools.check import *


urlpatterns = [
    # path('admin/', admin.site.urls),
    # path('get_dialogs/', views.get_content),
    path('', TemplateView.as_view(template_name='index.hftml')),
    # 标注文件
    path('mark/', mark),

    path('predict/', predict),
    # 更新信息
    path('updateInfo/', updateinfo),
    # 多分类标注
    path('mark_multiclassification/', mark_multiclassification),
    # 上传文件
    path('uploadFile/', upload_file),
    # 查找所有文件
    path('queryList/', query_list),
    # 下载文件
    path('FileDownload/', download_file),
    # 批量下载文件
    path('FilesDownload_/', download_files_),
    # 质检下载
    path('QualityDownload/', QualityDownload),
    # 批量下载文件
    path('FilesDownload/', download_files),
    # 删除文件
    path('deleteFile/', delete_file),
    # 请求类别下所有任务配置文件
    path('ReadConfig/', read_config),
    # 以文件名搜素
    path('filenameSearch/', filename_search),
    # 文件长度
    path('getFileLength/', get_file_length),
    # 检查文件
    path('checkFile/', file_check),
    # 给测试的数据
    path('toTest/', to_test),
    # 筛选classification/graph/marktool 所有没标完的数据
    path('SearchNotEmpty/', search_not_empty),
    # 筛选某个人classification/graph/marktool 某个类别所有没标完的数据
    path('SearchUserNotEmptyFile/', search_user_not_empty_file),
    # 登陆
    path('Login/', login),
    # token 验证
    path('getUserInfo/', get_user_info),
    # 获取用户信息
    path('getUsersInfo/', get_users_info),
    # 创建账号
    path('createUser/', create_user),
    # 修改账号信息
    path('updateUser/', update_user),
    # 领取文件
    path('reqFromFileName/', req_from_filename),
    # 查询faq标签分布
    path('getTagDistribution/', get_tag_distribution),
    # 知识图谱质检
    path('GraphCheck/', graph_check),
    # 删除某文件某段落所有标签
    path('AllRelationDelete/', all_relation_delete),
    # 标注数据退回
    path('chronoBreak/', chrono_break),
    # 提交质检
    path('submitCheck/', submit_check),
    # 查看提交质检的数据
    path('QueryCheckFile/', query_check_file),
    # 质检按钮
    path('check/', check),
    # 计算准确率
    path('caculateRate/', caculate_rate),
    # 统计标注人员标注数量
    path('selectEveryoneMarkedCount/', select_everyone_marked_count)
]

# 项目名.views.
handler404 = "marktool.src.utils.error.api_not_found"
handler500 = "marktool.src.utils.error.api_error"

