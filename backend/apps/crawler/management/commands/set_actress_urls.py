"""
Django管理命令 - 为女友设置URL
"""

import random
from django.core.management.base import BaseCommand
from apps.actresses.models import Actress


class Command(BaseCommand):
    help = '为女友设置URL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-actresses',
            type=int,
            default=100,
            help='最大设置女友数量'
        )

    def handle(self, *args, **options):
        max_actresses = options['max_actresses']
        
        self.stdout.write(
            self.style.SUCCESS(f'🔗 开始为女友设置URL')
        )

        # 获取没有URL的女友
        actresses = Actress.objects.filter(
            source_url__isnull=True
        ).exclude(
            profile_image=''
        )[:max_actresses]

        if not actresses:
            actresses = Actress.objects.filter(
                source_url=''
            ).exclude(
                profile_image=''
            )[:max_actresses]

        self.stdout.write(f'📋 找到 {len(actresses)} 个女友需要设置URL')

        # 设置URL
        base_urls = [
            'https://avmoo.website/cn/star/',
            'https://avmoo.cyou/cn/star/',
        ]

        success_count = 0
        for actress in actresses:
            try:
                # 生成一个基于姓名的伪随机ID
                actress_id = f"{abs(hash(actress.name)) % 1000000:06x}"
                base_url = random.choice(base_urls)
                actress.source_url = f"{base_url}{actress_id}"
                actress.save()
                
                success_count += 1
                self.stdout.write(f'  ✅ {actress.name}: {actress.source_url}')
                
            except Exception as e:
                self.stdout.write(f'  ❌ {actress.name}: {e}')

        self.stdout.write(f'\n🎉 完成！成功设置 {success_count} 个女友的URL')

        # 显示统计
        total_with_url = Actress.objects.exclude(source_url__isnull=True).exclude(source_url='').count()
        total_actresses = Actress.objects.count()
        
        self.stdout.write(f'📊 统计:')
        self.stdout.write(f'  有URL女友: {total_with_url}')
        self.stdout.write(f'  总女友数: {total_actresses}')
        self.stdout.write(f'  覆盖率: {total_with_url/max(total_actresses,1)*100:.1f}%')
