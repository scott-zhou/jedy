
public class LocalStaticFunc {
  public static void main(String[] args) {
    int amount = cal(6);
  }


  public static int cal(int max) {
    int amount = 0;
    for (int i=0; i<max; i++) {
      amount += i;
    }
    amount = amount - 3;
    amount /= 2;
    return amount;
  }

}
