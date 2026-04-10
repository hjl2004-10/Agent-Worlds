/**
 * 精灵图名称映射配置
 * 将精灵 ID 映射到友好的显示名称
 */

// 16x16 精灵 (基础角色) - ID 不带后缀
const SPRITE_NAMES_16X: Record<string, string> = {
  'Adam': '亚当',
  'Alex': '亚历克斯',
  'Amelia': '阿米莉亚',
  'Ash': '艾什',
  'Bob': '鲍勃',
  'Bruce': '布鲁斯',
  'Dan': '丹',
  'Edward': '爱德华',
  'Lucy': '露西',
  'Molly': '莫莉',
};

// 48x48 精灵 (高清角色) - ID 带 _48x48 后缀
const SPRITE_NAMES_48X: Record<string, string> = {
  'Postman_1_48x48': '邮递员 A',
  'Postman_2_48x48': '邮递员 B',
  'Postman_3_48x48': '邮递员 C',
  'Scout_1_48x48': '侦察兵 A',
  'Scout_2_48x48': '侦察兵 B',
  'Scout_3_48x48': '侦察兵 C',
  'Scout_4_48x48': '侦察兵 D',
  'Scout_5_48x48': '侦察兵 E',
  'Scout_6_48x48': '侦察兵 F',
  'Skeleton_1_48x48': '骷髅',
  'Swimmers_48x48': '游泳者',
  'Zombie_1_48x48': '僵尸 A',
  'Zombie_2_48x48': '僵尸 B',
};

// 合并所有映射
export const SPRITE_NAMES: Record<string, string> = {
  ...SPRITE_NAMES_16X,
  ...SPRITE_NAMES_48X,
};

/**
 * 获取精灵的友好显示名称
 * @param spriteId 精灵 ID
 * @returns 友好名称，如果未找到则返回原始 ID
 */
export function getSpriteDisplayName(spriteId: string): string {
  // 48x48 精灵不显示后缀
  if (spriteId.endsWith('_48x48')) {
    return SPRITE_NAMES[spriteId] || spriteId;
  }
  // 16x16 精灵显示名称
  return SPRITE_NAMES[spriteId] || spriteId;
}

/**
 * 将精灵 ID 列表转换为 Select 组件的 options
 * @param sprites 精灵 ID 列表
 * @returns Select options 数组
 */
export function spriteIdsToOptions(sprites: string[]): Array<{ value: string; label: string }> {
  // 分类: 16x 和 48x
  const sprites16x = sprites.filter(s => !s.endsWith('_48x48'));
  const sprites48x = sprites.filter(s => s.endsWith('_48x48'));

  // 排序
  sprites16x.sort();
  sprites48x.sort();

  // 构建 options
  const options: Array<{ value: string; label: string }> = [];

  // 16x 分组
  if (sprites16x.length > 0) {
    options.push({ value: '__group_16x__', label: '── 16x 基础角色 ──' });
    sprites16x.forEach(id => {
      options.push({ value: id, label: getSpriteDisplayName(id) });
    });
  }

  // 48x 分组
  if (sprites48x.length > 0) {
    options.push({ value: '__group_48x__', label: '── 48x 高清角色 ──' });
    sprites48x.forEach(id => {
      options.push({ value: id, label: getSpriteDisplayName(id) });
    });
  }

  return options;
}
