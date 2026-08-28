import re

with open(r'C:\Users\intel\Desktop\peridot\thermal-india-charge-improved.conf', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('trig\t44000\t44500\t45000\t45300\t45500\t45700\t45800\t45900\t45950\t46000', 'trig\t46000\t46500\t47000\t47300\t47500\t47700\t47800\t47900\t47950\t48000')
text = text.replace('clr\t43000\t44200\t44700\t45000\t45200\t45400\t45600\t45700\t45800\t45850', 'clr\t45000\t46200\t46700\t47000\t47200\t47400\t47600\t47700\t47800\t47850')
text = text.replace('trig\t15000\t44000\t44500\t45000\t45500\t45800\t45900\t46000', 'trig\t15000\t46000\t46500\t47000\t47500\t47800\t47900\t48000')
text = text.replace('clr\t14000\t43000\t44000\t44500\t45000\t45300\t45500\t45700', 'clr\t14000\t45000\t46000\t46500\t47000\t47300\t47500\t47700')
text = text.replace('target\t0\t44000\t44500\t45000\t45500\t45800\t45900\t46000', 'target\t0\t46000\t46500\t47000\t47500\t47800\t47900\t48000')

with open(r'C:\Users\intel\Desktop\peridot\thermal-india-charge-improved.conf', 'w', encoding='utf-8') as f:
    f.write(text)
