from discord.ext import commands
import re
import math

time_regex = re.compile("(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}


class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        matches = time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument("{} is an invalid time-key! h/m/s/d are valid!".format(k))
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))
        return time



class DMCConverter_Ctx(commands.Converter):
    async def convert(self, ctx, argument: str):
        try:
            value = argument.lower()
            value = value.replace("⏣", "").replace(",", "").replace("k", "e3").replace("m", "e6").replace(" mil", "e6").replace("mil", "e6").replace("b", "e9")
            if 'e' not in value:
                return int(value)
            value = value.split("e")

            if len(value) > 2: raise Exception(f"Invalid number format try using 1e3 or 1k, provided: {argument}")

            price = value[0]
            multi = int(value[1])
            price = float(price) * (10 ** multi)

            return int(price)
        except Exception as e:
            return Exception(f"Invalid number format try using 1e3 or 1k, provided: {argument}")


def millify(n):
    n = float(n)
    millnames = ['',' K',' Mil',' Bil',' T']
    millidx = max(0,min(len(millnames)-1,
                        int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

    return '{:.0f}{}'.format(n / 10**(3 * millidx), millnames[millidx])

def clean_code(content):
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:])[:-3]
    else:
        return content

#create an function to convert a dict to a tree and return it as string and use characters to display the tree, where  is a branch, ├─ is a branch with a child, └─ is a branch with a child and ─ is a child
def dict_to_tree(data, indent=0):
    tree = ""
    for i, (key, value) in enumerate(data.items()):
        tree += "\n" + "│  "*indent
        if isinstance(value, (dict, list)):
            tree += f"├─{key}:"
            if isinstance(value, dict):
                tree += dict_to_tree(value, indent=indent+1)
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    tree += "\n" + "│  "*(indent+1) + f"├─{key}[{index}]:"
                    if isinstance(item, (dict, list)):
                        tree += dict_to_tree(item, indent=indent+2)
                    else:
                        tree += "\n" + "│  "*(indent+2) + str(item)
        else:
            if i == len(data)-1:
                tree += f"└─{key}: {value}"
            else:
                tree += f"├─{key}: {value}"
    return tree

def get_bar(per: int):
    emojis = {
        "start_fill": "<:bar_start_fill:1149296377222930463>",
        "start_empty": "<:bar_start_empty:1149296657893171294>",
        "mid_fill": "<:bar_mid_fill:1149298022287679538>",
        "mid_empty": "<:bar_mid_empty:1149298212021211136>",
        "end_fill": "<:bar_end_fill:1149297916037582858>",
        "end_empty": "<:bar_end_empty:1149297776535027733>",
    }

    num_fill = int(per / 10)
    num_empty = 10 - num_fill
    if per == 0:
        bar = emojis["start_empty"] + (emojis["mid_empty"] * 8) + emojis["end_empty"]
    elif per == 100:
        bar = emojis["start_fill"] + (emojis["mid_fill"] * 8) + emojis["end_fill"] 
    else:
        bar = (emojis["start_fill"]) + (emojis['mid_fill']*(num_fill-1)) + (emojis['mid_empty']*(num_empty-1)) + (emojis['end_empty'])

    return bar