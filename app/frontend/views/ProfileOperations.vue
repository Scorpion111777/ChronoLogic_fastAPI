<script setup>

</script>

<template>
  <main class="profile_operations_page">

    <header class="app-header">
      <div class="row">
        <button class="header-back-link col-1">← Назад</button>
          <img src="../assets/icons/logo.svg" alt="Chronologic Logo" class="header-logo-img col-10" />
          <div class="header-user-icon col-1"></div>
      </div>
    </header>

    <div class="container">
      <div class="worker">
        <div class="header-user-icon col-1"></div>
        <div>
          <h5>Ім'я працівника</h5>
          <p>його посада</p>
          <p>example@gmail.com</p>
        </div>
        <div class='img-container'>
         <img src="../assets/icons/Vector.png" @click="">
        </div>
      </div>
      <div class="table-operations">
        <div class="operations_add_container">
          <button id="operations_add_button">Додати послідовність</button>
        </div>
        <div class="profile_table_operations">
          <table class="operations-table">
            <thead>
              <tr>
                <th>№</th>
                <th>№ Тех. операції</th>
                <th>Назва технологічної операції</th>
                <th>Затрати часу, хв</th>
                <th>Розряд</th>
                <th>Обладнання</th>
                <th>Технічні умови</th>
                <th>Виконавець</th>
                <th></th>
              </tr>
            </thead>


          </table>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
#operations_add_button{
  background: white;
  padding: 10px;
  border: 1px solid #4E48EB;
  border-radius:  10px;
}
.operations_add_container{
  margin-top: 20px;
  margin-left: 54px;
  margin-bottom:31px;
}
.profile_operations_page{
  width: 100%;
  min-height: 100vh;
  background-color: #f4f5f7;
  box-sizing: border-box;
}
.table-operations{
  background-color: #ffffff;
  height: auto;
  padding-top: 20px;
  padding-bottom: 20px;
  border-radius: 10px;
}
.img-container{
  padding: 20px 10px 10px 20px;
}
.worker{
  display: flex;
  align-items:center;
  margin: 70px 0 15px 20px;
  padding: 22px 17px 10px 29px;
  background-color: #ffffff;
  border: 1px solid #4545B5;
  border-radius: 10px;
  width: fit-content;
  font-family: inherit;
}
.row{
  width: 100%;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 15px 15px 30px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  width: 100%;
  box-sizing: border-box;
}

.header-user-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: #f0f0f0;
  border: 1px solid #ddd;
  margin-right:15px;
}
.header-back-link {
  text-decoration: none;
  color: #4e48eb;
  font-size: 16px;
  font-weight: 500;
  background-color: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: inherit;
}

</style>