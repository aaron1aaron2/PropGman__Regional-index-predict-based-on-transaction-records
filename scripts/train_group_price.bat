@REM 關掉回傳命令，不會回傳 bat 程式碼本身
@echo off 

set gp_num=10
set output_folder_root="./output/test-group-price"

for /L %%X in (0,1,%gp_num%) do (
    echo "group%%X"

    python train.py --time_slot 1440 --num_his 3 --num_pred 1 --batch_size 16 ^
                    --max_epoch 50 --patience 100 --learning_rate 0.0001 ^
                    --traffic_file "./data/train_data/basic/train_data/mean_group%%X_dist3000.h5" ^
                    --SE_file "./data/train_data/basic/SE_data/group%%X/SE.txt" ^
                    --model_file %output_folder_root%/group%%X/model.pkl ^
                    --log_file %output_folder_root%/group%%X/log.txt ^
                    --output_folder %output_folder_root%/group%%X/ ^
                    --device cpu
)

pause