close all;
clear all;
for i=1:10
    [status,result]=system('python client_app.py 127.0.0.1 10000 apptest\out2 -r Tpm Tpco Fzco Fzm Tzm -f apptest\client_2.input');
    if status==0
        result=strrep(result,'''','"');
        data=loadjson(result);
        data   
    else
        'blad klienta'
    end
end
