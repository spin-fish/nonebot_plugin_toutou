from nonebot import on_startswith, on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent,PrivateMessageEvent
from nonebot.rule import Rule
from nonebot.params import State
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Bot, Event
from time import time
import json

"""超级用户权限"""
SUPERUSER = 1234567  # 在此设置超级用户（审核上传目标）
# 仅许可超级用户
async def from_superuser(bot, event) :
    if event.user_id == SUPERUSER :
        return True
    else :
        return False

"""json与txt快速读写"""
def q_load(filename) :
    with open(filename) as f :
        return json.load(f)
def q_dump(obj, filename) :
    with open(filename, "w") as f :
        json.dump(obj, f)

"""常用的Rule"""
# 仅许可私聊
async def private_only(bot, event) -> bool:
    if isinstance(event, PrivateMessageEvent) :
        return True
    return False
# 仅许可群聊
async def group_only(bot, event) -> bool:
    if isinstance(event, GroupMessageEvent) :
        return True
    else :
        return False

"""插件本体"""
file = lambda filename : f"toutou的目录！！！/{filename}.json"
legal_target = q_load(file("legal_target"))
forbid = q_load(file("forbid"))
apply = q_load(file("apply"))
record = {}

toutou = on_startswith(["透透"], priority=10, rule=Rule(group_only), block=True)
@toutou.handle()
async def toutou_handle(bot: Bot, event: Event) :
    global apply
    target = str(event.get_message())[2:].strip()
    if not target :
        await toutou.finish()
    # 透机器人则拒绝（可以进行设置）
    if "~~~机器" in target :
        await toutou.finish("不准透机器人")
    # 合法请求进行复读
    elif target in legal_target :
        # 消息量控制
        try :
            last = record[str(event.group_id)]
        except KeyError:
            last = record[str(event.group_id)] = ["", int(time())]
        record[str(event.group_id)] = [target, int(time())]
        if (last[0] == target) and (time() - last[1] <= 30) :
            await toutou.finish()
        await toutou.finish(event.get_message())
    # 非法请求直接无视
    elif target in forbid :
        await toutou.finish()
    # 未知请求进行审核
    elif (len(target) <= 20) and (not "CQ" in target) :
        for app in apply :
            if target == app["target"] :
                await toutou.finish()
        apply.append({
            "user" : event.user_id,
            "group" : event.group_id,
            "target" : target
        })
        q_dump(apply, file("apply"))
        await bot.send_private_msg(
            user_id= SUPERUSER,
            message= "[新的审核：透透]\n审核指令：#审核透透"
        )
        await toutou.finish("（新的target已经提交审核）")
    else :
        await toutou.finish()

toutou_check = on_command("审核透透", priority=5, rule=Rule(private_only) & from_superuser, block=True)
@toutou_check.handle()
async def toutou_check_handle(bot: Bot) :
    if apply :
        app = apply[0]
        msg = f"[审核透透目标]\n来自群：{app['group']}\n申请者：{app['user']}"
        msg += f"\n目标：{app['target']}\n\n[是][否][暂留][忽略]"
        await toutou_check.send(msg)
    else :
        await toutou_check.finish("没有待审核的透透")

@toutou_check.got("decision")
async def get_decision(bot: Bot, state:T_State=State()) :
    global apply, legal_target, forbid
    if str(state["decision"]) == "是" :
        app = apply[0]
        if not app["target"] in legal_target :
            legal_target.append(app["target"])
            await bot.send_group_msg(
                group_id=app["group"],
                message=f"经审核，{app['target']}已经可以透了，试试在群里“透透{app['target']}”吧！"
            )
            q_dump(legal_target, file("legal_target"))
    elif str(state["decision"]) == "否" :
        forbid.append(apply[0]["target"])
        q_dump(forbid, file("forbid"))
    elif str(state["decision"]) == "忽略" :
        pass
    else :
        await toutou_check.finish("已取消本次审核")
    del apply[0]
    q_dump(apply, file("apply"))
    await toutou_check.finish("处理成功")
