public class Main {

    public static void main(String[] args) {
        People p = People.getPeople(1);
        int speed = p.speed();
        People otherp = People.getPeople(3);
        speed = otherp.speed();
    }
}
