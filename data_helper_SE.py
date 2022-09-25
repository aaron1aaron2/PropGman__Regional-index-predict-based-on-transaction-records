# encoding: utf-8
"""
Author: yen-nan ho
Contact: aaron1aaron2@gmail.com
GitHub: https://github.com/aaron1aaron2
Create Date:  2022.09.25
"""
import os
import argparse
import pandas as pd

from PropGman.utils import *
from PropGman.spatial_embedding import *

pd.options.mode.chained_assignment = None  # default='warn'

def get_args():
    parser = argparse.ArgumentParser()

    # data
    parser.add_argument('--file_path', type=str, default='data/youbike_sort/spot_info.csv')
    parser.add_argument('--output_folder', type=str, default='output/train data/SE')
    parser.add_argument('--id_col', type=str, default='sno', help='點的編號欄位')
    parser.add_argument('--group_col', type=str, default='sarea', help='群組欄位(youbike 資料以區為單位分區域)')
    parser.add_argument('--group', type=str, default=None, help='使用的群組(需要指定 group_col)，格式: XX區,XX區')

    parser.add_argument('--coordinate_col', type=str, default=None, help='點的經緯度欄位(當需要計算距離時)，格式: 24.1580,121.6222')
    parser.add_argument('--longitude_col', type=str, default='lng', help='經度(當 --coordinate_col 未設定時會使用)')
    parser.add_argument('--latitude_col', type=str, default='lat', help='緯度(當 --coordinate_col 未設定時會使用)')

    # Adj martix
    parser.add_argument('--distance_method', type=str, default='linear distance')
    parser.add_argument('--adj_threshold', type=float, default=0.1, help='兩點關係程度的門檻值')

    # Node2vec
    parser.add_argument('--is_directed', type=bool, default=True)
    parser.add_argument('--p', type=float, default=2, help='控制走訪時，走回頭路的機率。p高可以減少走訪時回頭的機率。')
    parser.add_argument('--q', type=float, default=1, help='控制走訪時，走訪深度。q>1 頃向 BFS， q<1 頃向 DFS。')
    parser.add_argument('--num_walks', type=int, default=100, help='跑過每個節點的次數')
    parser.add_argument('--walk_length', type=int, default=80,  help='每個節點走訪的次數')

    # word2vec
    parser.add_argument('--dimensions', type=int, default=64, help='Word2Vec 的輸出向量維度，也是 SE 的維度')
    parser.add_argument('--window_size', type=int, default=10, help='Word2Vec 的 window size')
    parser.add_argument('--itertime', type=int, default=1000,  help='Word2Vec 的迭帶次數')

    args = parser.parse_args()

    return args 

if __name__ == "__main__":

    args = get_args()
    print("="*20 + '\n' + str(args))
    build_folder(args.output_folder)

    saveJson(args.__dict__, os.path.join(args.output_folder, 'configures.json'))

    Adj_file = os.path.join(args.output_folder, 'Adj.txt')
    SE_file = os.path.join(args.output_folder, 'SE.txt')

    # SE存在時就結束
    if os.path.exists(SE_file):
        print("SE_file is already build at ({})".format(SE_file))
        exit()

    # ADJ 資料
    if not os.path.exists(Adj_file):
        print("building Adj_file at ({})".format(Adj_file))

        # 準備資料
        if args.group != None:
            if args.coordinate_col != None:
                df = pd.read_csv(args.file_path, usecols=[args.id_col, args.coordinate_col, args.group_col], dtype=str)
            else:
                args.coordinate_col = 'coordinate'
                df = pd.read_csv(args.file_path, usecols=[args.id_col, args.longitude_col, args.latitude_col, args.group_col], dtype=str)
                df[args.coordinate_col] = df[args.latitude_col].str.strip() + ',' + df[args.longitude_col].str.strip()
                df.drop([args.longitude_col, args.latitude_col], inplace=True, axis=1)
                
            group_use_ls = args.group.split(',')
            df = df[df[args.group_col].isin(group_use_ls)]
        else:
            if args.coordinate_col != None:
                df = pd.read_csv(args.file_path, usecols=[args.id_col, args.coordinate_col], dtype=str)
            else:
                args.coordinate_col = 'coordinate'
                df = pd.read_csv(args.file_path, usecols=[args.id_col, args.longitude_col, args.latitude_col], dtype=str)
                df[args.coordinate_col] = df[args.latitude_col].str.strip() + ',' + df[args.longitude_col].str.strip()
                df.drop([args.longitude_col, args.latitude_col], inplace=True, axis=1)

        df = df[~df[args.coordinate_col].isna()]
        
        # 建立區域內連結
        print("number of nodes: {}".format(df.shape[0]))

        df_AB = get_one_way_edge(df, group=group_col, coor_col=coordinate_col, id_col=id_col)

        # 獲取各 edge 關係評估值
        print("shape of one way edge: {}".format(df_AB.shape))
        if args.distance_method ==  'linear distance':
            df_AB = get_linear_distance(df_AB) # 786 |308504 |2min 7s
        else:
            assert False, 'please set the parameter - `distance_method`'

        # 建立雙向 edge 和自己到自己 (可直接轉成 disatnce martix)
        df_2W = get_two_way_with_self(df, df_AB, coor_col=args.coordinate_col, id_col=args.id_col)

        # 計算 adj 值 (基於 GMAN 論文上的算法，越小關係越大)
        df_2W_adj = get_adj_value(df_2W, threshold=args.adj_threshold)

        df_2W_adj[['start_no', 'end_no', 'adj']].to_csv(Adj_file, sep=' ', index=False, header=False)

    print("building SE_file at ({})".format(SE_file))

    # 訓練 Note2Vec 資料 (使用原始 GMAN 作者的程式碼 -> https://github.com/zhengchuanpan/GMAN/tree/master/PeMS/node2vec)
    train_node2vec = generateSE.SEDataHelper(
            is_directed=args.is_directed, p=args.p, q=args.q, 
            num_walks=args.num_walks, walk_length=args.walk_length,
            dimensions=args.dimensions, window_size=args.window_size,
            itertime=args.itertime,
            Adj_file=Adj_file,
            SE_file=SE_file
        )

    train_node2vec.run()