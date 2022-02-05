function mostrar(id){
    if(document.getElementById(id).style.display === 'block'){
        document.getElementById(id).style.display = 'none';
    }else{
        document.getElementById(id).style.display = 'block';
    }
}

function toggle(){
    if(check.checked){
        document.getElementById('navegacao').style.width = '230px';
        document.getElementById('logo').style.marginLeft = '0px';
        document.getElementById('user-panel').style.height = '70px';
        document.getElementById('aside-profile-photo').style.height = '50px';
        document.getElementById('aside-profile-photo').style.width = '50px';
        document.getElementById('aside-profile-name').style.display = 'inline-block';
        document.getElementById('conteudo').style.width = 'calc(100% - 230px)';

        // document.getElementById('check').value = 'on'
        // console.log(document.getElementById('check').value)
    }else{
        document.getElementById('navegacao').style.width = '52px';
        document.getElementById('logo').style.marginLeft = '-230px';
        document.getElementById('user-panel').style.height = '60px';
        document.getElementById('aside-profile-photo').style.height = '35px';
        document.getElementById('aside-profile-photo').style.width = '35px';
        document.getElementById('aside-profile-name').style.display = 'none';
        document.getElementById('conteudo').style.width = 'calc(100% - 52px)';

        // console.log(document.getElementById('check').value)
    }
}

function colapseProfile(){
    if(document.getElementById('profile').style.height === '290px'){
        document.getElementById('nome').style.display = 'none';
        document.getElementById('mail').style.display = 'none';
        document.getElementById('photo').style.display = 'none';
        document.getElementById('desde').style.display = 'none';
        document.getElementById('footer-left').style.display = 'none';
        document.getElementById('footer-right').style.display = 'none';
        document.getElementById('profile').style.height = '0px';
        document.getElementById('profile').style.width = '0px'
    }else{
        document.getElementById('nome').style.display = 'block';
        document.getElementById('mail').style.display = 'block';
        document.getElementById('photo').style.display = 'block';
        document.getElementById('desde').style.display = 'block';
        document.getElementById('footer-left').style.display = 'block';
        document.getElementById('footer-right').style.display = 'block';
        document.getElementById('profile').style.height = '290px';
        document.getElementById('profile').style.width = '340px'
    }
}