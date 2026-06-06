# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
# """
# 关键词匹配工具
# 基于jieba分词实现文本与关键词的匹配
# """

# import jieba
# from typing import List, Set, Union


# class KeywordMatcher:
#     """
#     关键词匹配器
    
#     使用jieba分词对文本进行分析，然后与关键词表进行匹配
#     """
    
#     def __init__(self, keywords: Union[List[str], Set[str]] = None, 
#                  case_sensitive: bool = False,
#                  custom_dict: str = None):
#         """
#         初始化关键词匹配器
        
#         Args:
#             keywords: 关键词列表或集合
#             case_sensitive: 是否区分大小写，默认False
#             custom_dict: 自定义词典文件路径
#         """
#         self.keywords = set(keywords) if keywords else set()
#         self.case_sensitive = case_sensitive
        
#         # 如果不区分大小写，将关键词转为小写
#         if not self.case_sensitive:
#             self.keywords = {kw.lower() for kw in self.keywords}
        
#         # 加载自定义词典
#         if custom_dict:
#             jieba.load_userdict(custom_dict)

    
#     def add_keyword(self, keyword: str):
#         """
#         添加单个关键词
        
#         Args:
#             keyword: 要添加的关键词
#         """
#         if not self.case_sensitive:
#             keyword = keyword.lower()
#         self.keywords.add(keyword)
    
#     def add_keywords(self, keywords: List[str]):
#         """
#         批量添加关键词
        
#         Args:
#             keywords: 关键词列表
#         """
#         for keyword in keywords:
#             self.add_keyword(keyword)
    
#     def remove_keyword(self, keyword: str):
#         """
#         移除关键词
        
#         Args:
#             keyword: 要移除的关键词
#         """
#         if not self.case_sensitive:
#             keyword = keyword.lower()
#         self.keywords.discard(keyword)
    
#     def clear_keywords(self):
#         """清空所有关键词"""
#         self.keywords.clear()
    
#     def get_keywords(self) -> Set[str]:
#         """
#         获取当前所有关键词
        
#         Returns:
#             关键词集合
#         """
#         return self.keywords.copy()
    
#     def segment(self, text: str) -> List[str]:
#         """
#         对文本进行分词
        
#         Args:
#             text: 待分词的文本
            
#         Returns:
#             分词结果列表
#         """
#         if not text:
#             return []
        
#         words = list(jieba.cut(text))
        
#         # 如果不区分大小写，转为小写
#         if not self.case_sensitive:
#             words = [w.lower() for w in words]
        
#         return words
    
#     def match(self, text: str) -> bool:
#         """
#         判断文本是否包含关键词
        
#         Args:
#             text: 待匹配的文本
            
#         Returns:
#             如果文本中包含任意一个关键词则返回True，否则返回False
#         """
#         if not text or not self.keywords:
#             return False
        
#         # 对文本进行分词
#         words = self.segment(text)
        
#         # 将分词结果转为集合，并与关键词集合求交集
#         word_set = set(words)
#         matched = bool(word_set & self.keywords)
        
#         return matched
    
#     def match_all(self, text: str, keywords: List[str] = None) -> bool:
#         """
#         判断文本是否包含所有指定的关键词
        
#         Args:
#             text: 待匹配的文本
#             keywords: 关键词列表，如果不提供则使用已设置的关键词
            
#         Returns:
#             如果文本包含所有关键词则返回True，否则返回False
#         """
#         if not text:
#             return False
        
#         # 使用提供的关键词或已设置的关键词
#         target_keywords = set(keywords) if keywords else self.keywords
#         if not target_keywords:
#             return False
        
#         # 不区分大小写处理
#         if not self.case_sensitive:
#             target_keywords = {kw.lower() for kw in target_keywords}
        
#         # 对文本进行分词
#         words = self.segment(text)
#         word_set = set(words)
        
#         # 判断是否所有关键词都在分词结果中
#         return target_keywords.issubset(word_set)
    
#     def find_matched_keywords(self, text: str) -> List[str]:
#         """
#         找出文本中匹配的所有关键词
        
#         Args:
#             text: 待匹配的文本
            
#         Returns:
#             匹配到的关键词列表
#         """
#         if not text or not self.keywords:
#             return []
        
#         # 对文本进行分词
#         words = self.segment(text)
#         word_set = set(words)
        
#         # 找出匹配的关键词
#         matched_keywords = list(word_set & self.keywords)
        
#         return matched_keywords
    
#     def match_with_details(self, text: str) -> dict:
#         """
#         匹配文本并返回详细信息
        
#         Args:
#             text: 待匹配的文本
            
#         Returns:
#             包含匹配结果、分词结果、匹配到的关键词等信息的字典
#         """
#         if not text:
#             return {
#                 'matched': False,
#                 'text': '',
#                 'words': [],
#                 'matched_keywords': [],
#                 'total_keywords': len(self.keywords)
#             }
        
#         words = self.segment(text)
#         matched_keywords = self.find_matched_keywords(text)
        
#         return {
#             'matched': len(matched_keywords) > 0,
#             'text': text,
#             'words': words,
#             'matched_keywords': matched_keywords,
#             'total_keywords': len(self.keywords)
#         }
    
#     def batch_match(self, texts: List[str]) -> List[bool]:
#         """
#         批量匹配多个文本
        
#         Args:
#             texts: 文本列表
            
#         Returns:
#             匹配结果列表
#         """
#         return [self.match(text) for text in texts]
    
#     def batch_match_with_details(self, texts: List[str]) -> List[dict]:
#         """
#         批量匹配多个文本并返回详细信息
        
#         Args:
#             texts: 文本列表
            
#         Returns:
#             详细信息列表
#         """
#         return [self.match_with_details(text) for text in texts]


# # 便捷函数
# def quick_match(text: str, keywords: List[str], case_sensitive: bool = False) -> bool:
#     """
#     快速匹配函数（无需创建实例）
    
#     Args:
#         text: 待匹配的文本
#         keywords: 关键词列表
#         case_sensitive: 是否区分大小写
        
#     Returns:
#         匹配结果
#     """
#     matcher = KeywordMatcher(keywords=keywords, case_sensitive=case_sensitive)
#     return matcher.match(text)


# def quick_find_keywords(text: str, keywords: List[str], case_sensitive: bool = False) -> List[str]:
#     """
#     快速查找匹配的关键词（无需创建实例）
    
#     Args:
#         text: 待匹配的文本
#         keywords: 关键词列表
#         case_sensitive: 是否区分大小写
        
#     Returns:
#         匹配到的关键词列表
#     """
#     matcher = KeywordMatcher(keywords=keywords, case_sensitive=case_sensitive)
#     return matcher.find_matched_keywords(text)

