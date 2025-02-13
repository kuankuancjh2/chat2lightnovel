from openai import OpenAI
from groq import Groq
#import json
#import os
import copy
from threading import Thread
import time
import gradio as gr


models = []
seed = -1
clients = []
#自己整apikey

char_prompts = {
    "char1":
        "你是傲娇，女高中生，对我冷淡，但暗恋我，容易吃醋。和char2经常拌嘴，虽然不承认但和char2关系很好。",
    "char2":
        "你是我的妹妹，高中生，有恋兄情结，但有点害羞。和char1经常拌嘴，虽然不承认但和char1关系很好。"
    }

chars = ["char1", "char2"]

prompts = [
    [
        {"role": "system", "content": "故事发生在日本高中的教室里，我（user）坐在char1的前面。现在正处于下课时间。"}, 
        {"role": "system", "content": "所有角色的设定如下（还有user这名角色，但你不能以user的身份发言）：" + str(list((o_char + ":" + char_prompts[o_char]) for o_char in chars))},
        {"role": "system", "content": "你要进行角色扮演。不要出戏，或说出思考过程，要按照人设进行，且说的话符合情景，不要出现奇怪的字符，或是换成英语。"},
        {"role": "system", "content": "你需要决定以哪个人的身份发言，或者以旁白的身份发言（此时user为我，其他角色为第三人称）。要注意，有些角色在逻辑上无法发言，比如开始的时候char2不在教室里，所以除非让她进来，否则无法发言。"}, 
        {"role": "system", "content": "在你说话的句首加入：角色名: 。如果你以旁白的身份发言，可以不用加入。一次只能说一行话，不允许换行，说多行话，或者换人说话"},
        {"role": "system", "content": "你说的话需要符合现实情境，表述要清晰，语言要流畅，但不是说要过度解释，尽量不要让角色、事物、态度等等突然出现，保持对话更有条理。询问自己说的话是否合适之后再说，不要不经思考就说出来，但也不要联想过度，同时除非搞笑或剧情需要，不要重复的话或描写。"},
        {"role": "system", "content": "你需要想象你是 一本优秀的轻小说中的 一个人物，说的话是你自己的想法（但不是说你是一个活在书中的人）。"}
    ],[
        {"role": "system", "content": "故事发生在日本高中的教室里，我（user）坐在char1的前面。现在正处于下课时间。"}, 
        {"role": "system", "content": "所有角色的设定如下（还有user这名角色言）：" + str(list((o_char + ":" + char_prompts[o_char]) for o_char in chars))},
        {"role": "system", "content": "这是一本轻小说中的一段，你需要斟酌这些话语是否合适，是否符合人设，逻辑正确等等。并向我提出建议，而不是写文章或者续写。字数在1000字以内，不要重复设定，你不要续写，而是从轻小说的角度为我提供建议。"},
    ]
]

        
global_messages = [{"role": "system", "content": "_"}]


if __name__ == "__main__":
    with gr.Blocks() as demo:
            
        class chat_area(gr.Blocks):
            
            def __init__(self, chatlabel, usage, scale=1, is_thin = False):
                super().__init__()
                self.messages = [{"role": "system", "content": "_"}]
                self.usage = usage
                self.is_thin = is_thin
            
                self.components(scale, chatlabel)
                                
                def request_state_change():
                    self.request_state = not self.request_state
                                
                self.request.click(fn=lambda request: "❌取消生成" if request == "请求生成" else "请求生成", inputs=self.request, outputs=self.request).then(fn=request_state_change).then(fn=lambda request: self.request_click() if request == "❌取消生成" else self.messages, inputs=self.request, outputs=self.chatbot).then(fn=lambda: "请求生成", outputs=self.request)
                
                self.chatbot.edit(fn=self.chatbot_edit, inputs=self.chatbot, outputs=self.chatbot)
                
                self.retry.click(fn=lambda request, auto: "❌取消生成" if request == "请求生成" and auto else "请求生成", inputs=[self.request, self.retry_auto_request], outputs=self.request).then(fn=self.retry_click, outputs=self.chatbot).then(fn=lambda auto: request_state_change() if auto else None, inputs=self.retry_auto_request).then(fn=lambda auto: self.request_click() if auto else self.messages, inputs=self.retry_auto_request, outputs=self.chatbot).then(fn=lambda: "请求生成", outputs=self.request)
                
                self.send.submit(fn=lambda request, auto: "❌取消生成" if request == "请求生成" and auto else "请求生成", inputs=[self.request, self.submit_auto_request], outputs=self.request).then(fn=self.user_input, inputs = self.send, outputs = [self.send, self.chatbot]).then(fn=lambda auto: request_state_change() if auto else None, inputs=self.submit_auto_request).then(fn=lambda auto: self.request_click() if auto else self.messages, inputs=self.submit_auto_request, outputs=self.chatbot).then(fn=lambda: "请求生成", outputs=self.request)

            def components(self, scale, chatlabel):
                with gr.Column(scale=scale):
                    self.chatbot = gr.Chatbot(self.messages, label=chatlabel, type="messages", editable="all", line_breaks=True)
                    with gr.Row():
                        self.send = gr.Textbox(label="发送消息", info="输入文字，回车提交", scale=5)
                        if not self.is_thin:
                            with gr.Column():
                                self.request = gr.Button("请求生成")
                                self.retry = gr.Button("重新生成")
                        else:
                            with gr.Row():
                                self.request = gr.Button("请求生成")
                                self.retry = gr.Button("重新生成")
                        self.request_state = False
                    with gr.Row():
                        self.submit_auto_request = gr.Checkbox(label="发送时自动请求生成", interactive=True, value=True)
                        self.retry_auto_request = gr.Checkbox(label="重新生成时自动请求生成", interactive=True, value=True)
                        
                                                    
            def generate(self, messages, usage):
                global seed, global_messages
                output = ""
                while output == "":
                    seed += 1000
                    class llm_core_request(Thread):
                        def run(self):
                            input = prompts[usage] + messages + [{"role": "user", "content": "_"}]
                            llm = clients[usage].chat.completions.create(messages=input,model=models[usage],seed=seed)
                            print(llm)
                            self.answer_ = llm.choices[0].message
                            
                    llm_request = llm_core_request()
                    llm_request.start()
                    while llm_request.is_alive():
                        time.sleep(0.1)
                        print(self.request_state)
                        if not self.request_state:
                            if usage == 0:
                                global_messages = messages + []
                            return messages
                    answer = llm_request.answer_
                    output = answer.content
                    try:
                        output = output.split("</think>")[-1].strip()
                    except:
                        pass
                    if output:
                        if messages[-1]["role"] == "assistant":
                            messages.append({"role": "assistant", "content": messages[-1]["content"] + "\n\n" + output})
                            del messages[-2]
                        else:
                            messages.append({"role": "assistant", "content": output})
                if usage == 0:
                    global_messages = messages + []
                return messages
   
            def request_click(self):
                global global_messages
                print(self.request.value)
                if self.usage == 0:
                    self.messages = self.generate(self.messages, self.usage)
                    global_messages = self.messages + []
                else:
                    history = ""
                    for i in self.generate(global_messages, self.usage)[-1].split("\n\n")[1:] :
                        history += i + "\n\n"
                    self.messages = history.strip()
                                       
                self.request_state = False
                return self.messages
                                
            def chatbot_edit(self, chatbot):
                global global_messages
                for message in chatbot:
                    del message["metadata"]
                    del message["options"]
                    if not message["content"]:
                        del message
                print(self.messages)
                self.messages = chatbot
                if self.usage == 0:
                    global_messages = self.messages + []
                return self.messages

            
            def retry_click(self):
                global global_messages
                if self.messages[-1]["role"] != "system":
                    if not self.is_thin:
                        history = ""
                        for i in self.messages[-1]["content"].split("\n\n")[:-1]:
                            history += i + "\n\n"
                        if history.strip():
                            self.messages.append({"role": "assistant", "content": history.strip()})
                            del self.messages[-2]
                        else:
                            del self.messages[-1]
                    else:
                        del self.messages[-1]
                global_messages = self.messages + []
                return self.messages
            
            def user_input(self, input):
                if self.messages[-1]["role"] == "user":
                    self.messages.append({"role": "user", "content": self.messages[-1]["content"] + "\n\n" + input})
                    del self.messages[-2]
                else:
                    self.messages.append({"role": "user", "content": input})
                return "", self.messages
        

        with gr.Row():
            with chat_area("对话区", 0, scale = 3):
                None
            with gr.Accordion():
                with chat_area("建议区", 1, is_thin=True):
                    None
                
    demo.launch(debug=True)

