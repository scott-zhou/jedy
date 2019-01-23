public class Main {

    public static void main(String[] args) {
        Data d = new Data();
        int x = d.pub_v;
        int y = d.get_v();
        d.pub_v = y;
        d.set_v(x);
        x = d.pub_v;
        y = d.get_v();
    }
}
